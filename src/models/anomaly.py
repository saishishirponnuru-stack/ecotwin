"""
EcoTwin Anomaly Detection Module
==================================
Detects abnormal energy consumption patterns using a layered approach:

1. Residual-based detection: flags when actual energy significantly exceeds
   the prediction model's expected energy (statistical process control)
2. Isolation Forest: catches multivariate anomalies in the feature space
3. Severity classification: Watch / Warning / Critical

Key principle: anomalies are CONTEXT-AWARE. High energy during high production
is normal. High energy during LOW production is anomalous.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.ensemble import IsolationForest
import warnings


@dataclass
class AnomalyResult:
    """Container for a single anomaly detection result."""
    index: int
    machine_id: str
    timestamp: str
    actual_kwh: float
    predicted_kwh: float
    deviation_kwh: float
    deviation_pct: float
    z_score: float
    severity: str  # 'normal', 'watch', 'warning', 'critical'
    confidence: float
    is_anomaly: bool
    possible_contributors: List[str]
    potential_saving_kwh: float

    def to_dict(self) -> Dict:
        return {
            'machine_id': self.machine_id,
            'timestamp': self.timestamp,
            'actual_kwh': round(self.actual_kwh, 4),
            'predicted_kwh': round(self.predicted_kwh, 4),
            'deviation_kwh': round(self.deviation_kwh, 4),
            'deviation_pct': round(self.deviation_pct, 2),
            'z_score': round(self.z_score, 2),
            'severity': self.severity,
            'confidence': round(self.confidence, 1),
            'is_anomaly': self.is_anomaly,
            'possible_contributors': self.possible_contributors,
            'potential_saving_kwh': round(self.potential_saving_kwh, 4),
        }


class AnomalyDetector:
    """
    Layered anomaly detection for manufacturing energy consumption.
    
    Combines residual-based statistical detection with Isolation Forest
    for robust, interpretable anomaly flagging.
    
    Usage:
        detector = AnomalyDetector()
        detector.fit(residuals_df, features_df)
        results = detector.detect(residuals_df, features_df, context_df)
    """

    # Severity thresholds (in standard deviations of residuals)
    SEVERITY_THRESHOLDS = {
        'watch': 1.5,
        'warning': 2.0,
        'critical': 3.0,
    }

    def __init__(
        self,
        contamination: float = 0.05,
        random_state: int = 42,
        use_isolation_forest: bool = True,
    ):
        """
        Initialize anomaly detector.
        
        Args:
            contamination: Expected proportion of anomalies (for Isolation Forest)
            random_state: Random seed
            use_isolation_forest: Whether to use Isolation Forest as secondary detector
        """
        self.contamination = contamination
        self.random_state = random_state
        self.use_isolation_forest = use_isolation_forest
        self.isolation_forest = None
        self.residual_stats: Dict[str, float] = {}
        self.is_fitted = False

    def fit(
        self,
        residuals: pd.Series,
        features: Optional[pd.DataFrame] = None,
    ) -> 'AnomalyDetector':
        """
        Fit the anomaly detector on training data residuals.
        
        Args:
            residuals: Prediction residuals (actual - predicted)
            features: Feature matrix for Isolation Forest (optional)
            
        Returns:
            self
        """
        # Compute robust residual statistics
        self.residual_stats = {
            'mean': float(residuals.mean()),
            'std': float(residuals.std()),
            'median': float(np.median(residuals)),
            'mad': float(np.median(np.abs(residuals - np.median(residuals)))),
            'q1': float(residuals.quantile(0.25)),
            'q3': float(residuals.quantile(0.75)),
        }

        # MAD-based robust sigma
        mad = self.residual_stats['mad']
        self.residual_stats['robust_sigma'] = (
            1.4826 * mad if mad > 0 else self.residual_stats['std']
        )

        # Fit Isolation Forest on feature space (including residuals)
        if self.use_isolation_forest and features is not None:
            iso_features = features.select_dtypes(include=[np.number]).copy()
            iso_features['residual'] = residuals.values

            self.isolation_forest = IsolationForest(
                contamination=self.contamination,
                random_state=self.random_state,
                n_estimators=200,
                max_samples='auto',
                n_jobs=-1,
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                self.isolation_forest.fit(iso_features)

        self.is_fitted = True
        return self

    def detect(
        self,
        residuals: pd.Series,
        features: pd.DataFrame,
        context: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Detect anomalies in the data.
        
        Args:
            residuals: Prediction residuals (actual - predicted)
            features: Feature matrix
            context: DataFrame with contextual info (machine_id, timestamp, etc.)
            
        Returns:
            DataFrame with anomaly detection results
        """
        if not self.is_fitted:
            raise RuntimeError("Detector must be fitted first")

        sigma = self.residual_stats['robust_sigma']
        median = self.residual_stats['median']

        # Compute z-scores using robust statistics
        z_scores = (residuals.values - median) / sigma if sigma > 0 else np.zeros(len(residuals))

        # Residual-based severity classification
        severity = np.where(
            np.abs(z_scores) >= self.SEVERITY_THRESHOLDS['critical'],
            'critical',
            np.where(
                np.abs(z_scores) >= self.SEVERITY_THRESHOLDS['warning'],
                'warning',
                np.where(
                    np.abs(z_scores) >= self.SEVERITY_THRESHOLDS['watch'],
                    'watch',
                    'normal',
                ),
            ),
        )

        # Isolation Forest anomaly scores
        iso_anomaly = np.zeros(len(residuals), dtype=bool)
        iso_scores = np.zeros(len(residuals))
        if self.isolation_forest is not None:
            iso_features = features.select_dtypes(include=[np.number]).copy()
            iso_features['residual'] = residuals.values
            iso_predictions = self.isolation_forest.predict(iso_features)
            iso_anomaly = iso_predictions == -1
            iso_scores = -self.isolation_forest.score_samples(iso_features)

        # Combined anomaly flag: residual-based OR isolation forest
        is_anomaly = (
            (np.abs(z_scores) >= self.SEVERITY_THRESHOLDS['warning'])
            | iso_anomaly
        )

        # Confidence: higher z-score = higher confidence that it's anomalous
        confidence = np.clip(np.abs(z_scores) / 5.0 * 100, 0, 99)

        # Potential saving: if energy is above expected, saving = deviation
        predicted = context.get('predicted_kwh', pd.Series(0, index=context.index))
        actual = context.get('actual_kwh', pd.Series(0, index=context.index))
        potential_saving = np.maximum(residuals.values, 0)

        results = pd.DataFrame({
            'machine_id': context.get('machine_id', 'Unknown'),
            'timestamp': context.get('timestamp', ''),
            'actual_kwh': actual,
            'predicted_kwh': predicted,
            'deviation_kwh': residuals.values,
            'deviation_pct': np.where(
                predicted > 0,
                (residuals.values / predicted) * 100,
                0.0,
            ),
            'z_score': z_scores,
            'severity': severity,
            'confidence': confidence,
            'is_anomaly': is_anomaly,
            'iso_forest_anomaly': iso_anomaly,
            'iso_forest_score': iso_scores,
            'potential_saving_kwh': potential_saving,
        }, index=residuals.index)

        return results

    def get_anomaly_summary(
        self, detection_results: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Summarize anomalies by machine.
        
        Args:
            detection_results: Output from detect()
            
        Returns:
            Summary DataFrame grouped by machine
        """
        anomalies = detection_results[detection_results['is_anomaly']]

        if anomalies.empty:
            return pd.DataFrame()

        summary = anomalies.groupby('machine_id').agg(
            anomaly_count=('is_anomaly', 'sum'),
            avg_deviation_pct=('deviation_pct', 'mean'),
            max_deviation_pct=('deviation_pct', 'max'),
            total_excess_kwh=('potential_saving_kwh', 'sum'),
            avg_confidence=('confidence', 'mean'),
            critical_count=('severity', lambda x: (x == 'critical').sum()),
            warning_count=('severity', lambda x: (x == 'warning').sum()),
        ).sort_values('total_excess_kwh', ascending=False)

        return summary

    def classify_anomaly_contributors(
        self,
        row: pd.Series,
        feature_importances: Optional[pd.DataFrame] = None,
        shap_values: Optional[np.ndarray] = None,
        feature_names: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Generate human-readable explanations for why an anomaly occurred.
        
        Uses a combination of rule-based logic and feature importance to
        identify likely contributors.
        
        Args:
            row: Single row of data with features and anomaly info
            feature_importances: Model feature importance scores
            shap_values: SHAP values for this prediction (optional)
            feature_names: Feature names corresponding to SHAP values
            
        Returns:
            List of natural-language contributor explanations
        """
        contributors = []

        # Rule-based diagnostic checks
        if 'tool_wear_min' in row.index:
            wear = row.get('tool_wear_min', 0)
            if wear > 180:
                contributors.append(
                    f"High tool wear ({wear:.0f} min) — may increase "
                    "cutting resistance and energy draw"
                )
            elif wear > 120:
                contributors.append(
                    f"Moderate tool wear ({wear:.0f} min) — approaching "
                    "maintenance threshold"
                )

        if 'process_temp_k' in row.index and 'air_temp_k' in row.index:
            temp_delta = row.get('process_temp_k', 0) - row.get('air_temp_k', 0)
            if temp_delta > 12:
                contributors.append(
                    f"High process-ambient temperature difference "
                    f"({temp_delta:.1f} K) — possible heat dissipation issue"
                )

        if 'idle_time_seconds' in row.index:
            idle = row.get('idle_time_seconds', 0)
            if idle > 120:
                contributors.append(
                    f"Extended idle time ({idle:.0f}s) — base-load power "
                    "consumed without production"
                )

        if 'maintenance_status' in row.index:
            status = row.get('maintenance_status', 'OK')
            if status == 'Overdue':
                contributors.append(
                    "Maintenance overdue — mechanical degradation may "
                    "increase energy consumption"
                )
            elif status == 'Due':
                contributors.append(
                    "Maintenance due — schedule preventive maintenance "
                    "to prevent further degradation"
                )

        if 'torque_nm' in row.index:
            torque = row.get('torque_nm', 0)
            if torque > 60:
                contributors.append(
                    f"Abnormally high torque ({torque:.1f} Nm) — possible "
                    "mechanical binding or material anomaly"
                )

        if 'rotational_speed_rpm' in row.index:
            rpm = row.get('rotational_speed_rpm', 0)
            if rpm < 1200:
                contributors.append(
                    f"Low rotational speed ({rpm:.0f} RPM) — may indicate "
                    "overload or speed controller issue"
                )

        # SHAP-based contributors (if available)
        if shap_values is not None and feature_names is not None:
            top_shap_indices = np.argsort(np.abs(shap_values))[-3:][::-1]
            for idx in top_shap_indices:
                if idx < len(feature_names):
                    fname = feature_names[idx]
                    sval = shap_values[idx]
                    direction = "increasing" if sval > 0 else "decreasing"
                    contributors.append(
                        f"{fname} is {direction} predicted energy "
                        f"(SHAP: {sval:+.4f} kWh)"
                    )

        if not contributors:
            contributors.append(
                "No single dominant contributor identified — "
                "recommend detailed investigation"
            )

        return contributors
