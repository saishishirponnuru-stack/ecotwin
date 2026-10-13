"""
EcoTwin Energy Prediction Model
================================
Predicts expected energy consumption per manufactured part based on
operating conditions (temperature, speed, torque, tool wear, etc.).

The prediction model enables:
1. Baseline energy estimation for normal operating conditions
2. Energy deviation detection (actual - predicted)
3. What-If simulation (modify parameters → predict new energy)

Models benchmarked: Ridge Regression, Random Forest, XGBoost, LightGBM
Selection based on: MAE, RMSE, MAPE, R² on time-aware validation split.
"""

import numpy as np
import pandas as pd
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
import joblib
import time
import warnings

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    mean_absolute_percentage_error,
)
from sklearn.preprocessing import StandardScaler

try:
    import xgboost as xgb
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False


@dataclass
class ModelMetrics:
    """Container for model evaluation metrics."""
    model_name: str
    mae: float
    rmse: float
    mape: float
    r2: float
    train_time_seconds: float
    n_features: int
    feature_names: list = field(default_factory=list)
    hyperparameters: dict = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> Dict:
        return {
            "model_name": self.model_name,
            "mae_kwh": round(self.mae, 6),
            "rmse_kwh": round(self.rmse, 6),
            "mape_pct": round(self.mape * 100, 2),
            "r2": round(self.r2, 4),
            "train_time_s": round(self.train_time_seconds, 2),
            "n_features": self.n_features,
            "hyperparameters": self.hyperparameters,
            "notes": self.notes,
        }

    def summary(self) -> str:
        return (
            f"{self.model_name}: MAE={self.mae:.6f} kWh, "
            f"RMSE={self.rmse:.6f} kWh, MAPE={self.mape*100:.2f}%, "
            f"R²={self.r2:.4f}, Train={self.train_time_seconds:.1f}s"
        )


class AnalyticalEnergyBaseline:
    """
    First-principles physical energy baseline.
    
    Computes theoretical electrical energy directly from kinematics and motor physics
    with ZERO training parameters:
        P_mech = Torque * (Speed * 2 * pi / 60)
        P_elec = P_mech / motor_efficiency
        Energy = (P_elec * (cycle_time / 60)) / 1000
    """
    def __init__(self, motor_efficiency: float = 0.85):
        self.motor_efficiency = motor_efficiency
        self.model_type = "analytical_physics"
        self.is_fitted = True
        self.feature_names = ['torque_nm', 'rotational_speed_rpm', 'cycle_time_minutes']

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Compute expected baseline energy from physical kinematics."""
        torque = X['torque_nm'] if 'torque_nm' in X.columns else X['Torque [Nm]']
        speed = X['rotational_speed_rpm'] if 'rotational_speed_rpm' in X.columns else X['Rotational speed [rpm]']
        if 'cycle_time_minutes' in X.columns:
            ct = X['cycle_time_minutes']
        elif 'product_type' in X.columns:
            ct = X['product_type'].map({'L': 1.5, 'M': 3.0, 'H': 5.0}).fillna(3.0)
        else:
            ct = 3.0

        p_mech = torque * (speed * 2.0 * np.pi / 60.0)
        p_elec = p_mech / self.motor_efficiency
        energy = (p_elec * (ct / 60.0)) / 1000.0
        return np.maximum(np.array(energy), 0.0)


class EnergyPredictor:
    """
    Predicts expected energy consumption per manufactured part.
    
    Supports multiple model backends and provides a unified interface
    for training, prediction, evaluation, and What-If simulation.
    
    Usage:
        predictor = EnergyPredictor()
        predictor.fit(X_train, y_train)
        predictions = predictor.predict(X_test)
        metrics = predictor.evaluate(X_test, y_test)
    """

    # Non-leaky operational features (excludes analytical target components: power_watts and cycle_time_minutes)
    NON_LEAKY_FEATURES = [
        'rotational_speed_rpm',
        'torque_nm',
        'tool_wear_min',
        'air_temp_k',
        'process_temp_k',
        'product_type_encoded',
        'shift_encoded',
        'maintenance_days_since',
        'ambient_temperature',
    ]

    # Legacy default features (kept for backward compatibility with existing saved artifacts)
    DEFAULT_FEATURES = [
        'power_watts',
        'rotational_speed_rpm',
        'torque_nm',
        'tool_wear_min',
        'air_temp_k',
        'process_temp_k',
        'cycle_time_minutes',
        'idle_time_seconds',
        'product_type_encoded',
        'shift_encoded',
        'maintenance_days_since',
        'ambient_temperature_c',
    ]

    TARGET = 'energy_kwh'


    def __init__(self, model_type: str = 'xgboost', random_state: int = 42):
        """
        Initialize energy predictor.
        
        Args:
            model_type: One of 'ridge', 'random_forest', 'xgboost', 'lightgbm'
            random_state: Random seed for reproducibility
        """
        self.model_type = model_type
        self.random_state = random_state
        self.model = None
        self.scaler = None
        self.feature_names = []
        self.is_fitted = False
        self.training_metrics: Optional[ModelMetrics] = None
        self.feature_ranges: Dict[str, Tuple[float, float]] = {}

        self._init_model()

    def _init_model(self):
        """Initialize the ML model based on model_type."""
        if self.model_type == 'ridge':
            self.model = Ridge(alpha=1.0, random_state=self.random_state)
            self.scaler = StandardScaler()

        elif self.model_type == 'random_forest':
            self.model = RandomForestRegressor(
                n_estimators=200,
                max_depth=12,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=self.random_state,
                n_jobs=-1,
            )

        elif self.model_type == 'xgboost':
            if not HAS_XGBOOST:
                raise ImportError("xgboost is not installed")
            self.model = xgb.XGBRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=self.random_state,
                n_jobs=-1,
                verbosity=0,
            )

        elif self.model_type == 'lightgbm':
            if not HAS_LIGHTGBM:
                raise ImportError("lightgbm is not installed")
            self.model = lgb.LGBMRegressor(
                n_estimators=300,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=1.0,
                random_state=self.random_state,
                n_jobs=-1,
                verbose=-1,
            )
        else:
            raise ValueError(
                f"Unknown model_type: {self.model_type}. "
                f"Choose from: ridge, random_forest, xgboost, lightgbm"
            )

    def fit(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        feature_names: Optional[list] = None,
    ) -> 'EnergyPredictor':
        """
        Train the energy prediction model.
        
        Args:
            X: Feature matrix
            y: Target variable (energy_kwh)
            feature_names: Optional list of feature names to use.
                           If None, uses all columns in X.
        
        Returns:
            self (for method chaining)
        """
        self.feature_names = feature_names or list(X.columns)
        X_train = X[self.feature_names].copy()

        # Store feature ranges for extrapolation detection
        for col in self.feature_names:
            self.feature_ranges[col] = (
                float(X_train[col].min()),
                float(X_train[col].max()),
            )

        # Scale features for Ridge regression
        if self.scaler is not None:
            X_train = pd.DataFrame(
                self.scaler.fit_transform(X_train),
                columns=self.feature_names,
                index=X_train.index,
            )

        start_time = time.time()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model.fit(X_train, y)
        train_time = time.time() - start_time

        self.is_fitted = True

        # Compute training metrics
        y_pred = self.predict(X[self.feature_names])
        self.training_metrics = self._compute_metrics(
            y, y_pred, train_time, "Training"
        )

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict expected energy consumption.
        
        Args:
            X: Feature matrix with same columns as training data
            
        Returns:
            Array of predicted energy values (kWh)
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before prediction")

        X_pred = X[self.feature_names].copy()

        if self.scaler is not None:
            X_pred = pd.DataFrame(
                self.scaler.transform(X_pred),
                columns=self.feature_names,
                index=X_pred.index,
            )

        predictions = self.model.predict(X_pred)
        # Energy cannot be negative
        predictions = np.maximum(predictions, 0.0)
        return predictions

    def evaluate(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        dataset_label: str = "Validation",
    ) -> ModelMetrics:
        """
        Evaluate model performance on a dataset.
        
        Args:
            X: Feature matrix
            y: True energy values
            dataset_label: Label for the evaluation (e.g., "Validation", "Test")
            
        Returns:
            ModelMetrics with MAE, RMSE, MAPE, R²
        """
        y_pred = self.predict(X)
        return self._compute_metrics(y, y_pred, 0.0, dataset_label)

    def _compute_metrics(
        self,
        y_true: pd.Series,
        y_pred: np.ndarray,
        train_time: float,
        label: str,
    ) -> ModelMetrics:
        """Compute evaluation metrics."""
        # Avoid MAPE issues with zero values
        mask = y_true > 0
        mape_val = (
            mean_absolute_percentage_error(y_true[mask], y_pred[mask])
            if mask.sum() > 0
            else float('inf')
        )

        return ModelMetrics(
            model_name=f"{self.model_type} ({label})",
            mae=mean_absolute_error(y_true, y_pred),
            rmse=np.sqrt(mean_squared_error(y_true, y_pred)),
            mape=mape_val,
            r2=r2_score(y_true, y_pred),
            train_time_seconds=train_time,
            n_features=len(self.feature_names),
            feature_names=self.feature_names.copy(),
            hyperparameters=self._get_hyperparameters(),
        )

    def _get_hyperparameters(self) -> dict:
        """Extract model hyperparameters."""
        if hasattr(self.model, 'get_params'):
            params = self.model.get_params()
            # Filter to key params only
            key_params = {
                'ridge': ['alpha'],
                'random_forest': ['n_estimators', 'max_depth', 'min_samples_split'],
                'xgboost': ['n_estimators', 'max_depth', 'learning_rate', 'subsample'],
                'lightgbm': ['n_estimators', 'max_depth', 'learning_rate', 'subsample'],
            }
            keys = key_params.get(self.model_type, [])
            return {k: params.get(k) for k in keys if k in params}
        return {}

    def compute_residuals(
        self, X: pd.DataFrame, y: pd.Series
    ) -> pd.DataFrame:
        """
        Compute prediction residuals for anomaly detection.
        
        Args:
            X: Feature matrix
            y: Actual energy values
            
        Returns:
            DataFrame with columns: actual, predicted, residual, 
            residual_pct, z_score
        """
        y_pred = self.predict(X)
        residuals = y.values - y_pred

        # Robust statistics for z-score (MAD-based)
        median_residual = np.median(residuals)
        mad = np.median(np.abs(residuals - median_residual))
        # MAD to sigma conversion: sigma ≈ 1.4826 × MAD
        robust_sigma = 1.4826 * mad if mad > 0 else np.std(residuals)

        z_scores = (residuals - median_residual) / robust_sigma if robust_sigma > 0 else np.zeros_like(residuals)

        result = pd.DataFrame({
            'actual_kwh': y.values,
            'predicted_kwh': y_pred,
            'residual_kwh': residuals,
            'residual_pct': np.where(
                y_pred > 0,
                (residuals / y_pred) * 100,
                0.0,
            ),
            'z_score': z_scores,
        }, index=y.index)

        return result

    def get_feature_importance(self) -> pd.DataFrame:
        """
        Get feature importance from the trained model.
        
        Returns:
            DataFrame with feature names and importance scores, sorted descending.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        if hasattr(self.model, 'feature_importances_'):
            importances = self.model.feature_importances_
        elif hasattr(self.model, 'coef_'):
            importances = np.abs(self.model.coef_)
        else:
            return pd.DataFrame()

        df = pd.DataFrame({
            'feature': self.feature_names,
            'importance': importances,
        }).sort_values('importance', ascending=False).reset_index(drop=True)

        # Normalize to percentages
        total = df['importance'].sum()
        if total > 0:
            df['importance_pct'] = (df['importance'] / total) * 100
        else:
            df['importance_pct'] = 0.0

        return df

    def check_extrapolation(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Check if input features are outside training data range.
        
        Args:
            X: Feature matrix to check
            
        Returns:
            DataFrame flagging out-of-range features per row
        """
        flags = pd.DataFrame(index=X.index)
        for col in self.feature_names:
            if col in self.feature_ranges and col in X.columns:
                low, high = self.feature_ranges[col]
                flags[f'{col}_extrapolation'] = (
                    (X[col] < low) | (X[col] > high)
                )
        flags['any_extrapolation'] = flags.any(axis=1)
        return flags

    def save(self, path: str):
        """Save the fitted model and scaler to disk."""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'model_type': self.model_type,
            'feature_names': self.feature_names,
            'feature_ranges': self.feature_ranges,
            'is_fitted': self.is_fitted,
            'training_metrics': self.training_metrics,
        }, path)

    @classmethod
    def load(cls, path: str) -> 'EnergyPredictor':
        """Load a fitted model from disk."""
        data = joblib.load(path)
        predictor = cls.__new__(cls)
        predictor.model = data['model']
        predictor.scaler = data['scaler']
        predictor.model_type = data['model_type']
        predictor.feature_names = data['feature_names']
        predictor.feature_ranges = data['feature_ranges']
        predictor.is_fitted = data['is_fitted']
        predictor.training_metrics = data['training_metrics']
        predictor.random_state = 42
        return predictor


def benchmark_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    feature_names: Optional[list] = None,
) -> Tuple[Dict[str, EnergyPredictor], pd.DataFrame]:
    """
    Benchmark all available models and return comparison.
    
    Args:
        X_train: Training features
        y_train: Training target
        X_val: Validation features  
        y_val: Validation target
        feature_names: Feature columns to use
        
    Returns:
        Tuple of (dict of fitted models, DataFrame of metrics comparison)
    """
    model_types = ['ridge', 'random_forest']
    if HAS_XGBOOST:
        model_types.append('xgboost')
    if HAS_LIGHTGBM:
        model_types.append('lightgbm')

    models = {}
    results = []

    for mtype in model_types:
        print(f"  Training {mtype}...")
        predictor = EnergyPredictor(model_type=mtype)
        predictor.fit(X_train, y_train, feature_names=feature_names)

        train_metrics = predictor.training_metrics
        val_metrics = predictor.evaluate(X_val, y_val, "Validation")

        results.append({
            'model': mtype,
            'train_mae': train_metrics.mae,
            'train_r2': train_metrics.r2,
            'val_mae': val_metrics.mae,
            'val_rmse': val_metrics.rmse,
            'val_mape_pct': val_metrics.mape * 100,
            'val_r2': val_metrics.r2,
            'train_time_s': train_metrics.train_time_seconds,
            'overfit_ratio': train_metrics.mae / val_metrics.mae if val_metrics.mae > 0 else 0,
        })

        models[mtype] = predictor
        print(f"    {val_metrics.summary()}")

    comparison = pd.DataFrame(results).sort_values('val_mae')
    return models, comparison
