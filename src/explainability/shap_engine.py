"""
SHAP Explainability Engine for EcoTwin.
"""
import logging
from typing import Dict, Any, List, Tuple, Union
import numpy as np
import pandas as pd

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    shap = None
    SHAP_AVAILABLE = False

logger = logging.getLogger(__name__)

class SHAPExplainer:
    """
    Computes SHAP values using TreeExplainer for energy prediction models.
    """
    
    def __init__(self, predictor: Any):
        """
        Initialize the SHAP Explainer.
        
        Args:
            predictor: The EnergyPredictor instance containing the fitted model.
        """
        self.predictor = predictor
        
        if not SHAP_AVAILABLE:
            logger.warning("SHAP is not installed. Explanations will not be available.")
            self.explainer = None
            return
            
        # The predictor should have a .model attribute which is the sklearn/xgboost estimator
        if not hasattr(self.predictor, 'model'):
            raise ValueError("Predictor must have a 'model' attribute.")
            
        try:
            self.explainer = shap.TreeExplainer(self.predictor.model)
        except Exception as e:
            logger.error(f"Failed to initialize TreeExplainer: {e}")
            self.explainer = None
            
        self.expected_value = getattr(self.explainer, "expected_value", None)
        if isinstance(self.expected_value, (np.ndarray, list)):
            self.expected_value = self.expected_value[0]

    def explain_single(self, row_features: pd.DataFrame) -> Dict[str, Any]:
        """
        Explain a single prediction.
        
        Args:
            row_features: A single row DataFrame containing features.
            
        Returns:
            Dictionary with SHAP values, base value, feature names, and top contributors.
        """
        if not SHAP_AVAILABLE or self.explainer is None:
            return {"error": "SHAP not available or explainer not initialized"}
            
        shap_values = self.explainer.shap_values(row_features)
        if isinstance(shap_values, list):
            shap_values = shap_values[0] # Handle multi-class / list outputs if any
            
        # For single row, shap_values might be 1D or 2D. Ensure 1D.
        if len(shap_values.shape) > 1 and shap_values.shape[0] == 1:
            shap_values = shap_values[0]
            
        feature_names = list(row_features.columns)
        row_values = row_features.iloc[0].values
        
        # Calculate contributors
        contributors = []
        for i, (name, val) in enumerate(zip(feature_names, shap_values)):
            direction = "increase" if val > 0 else "decrease"
            contributors.append((name, float(val), direction))
            
        # Sort by absolute impact
        contributors.sort(key=lambda x: abs(x[1]), reverse=True)
        
        return {
            "shap_values": shap_values.tolist(),
            "base_value": float(self.expected_value) if self.expected_value is not None else 0.0,
            "feature_names": feature_names,
            "top_contributors": contributors,
            "row_values": row_values.tolist()
        }

    def explain_batch(self, X: pd.DataFrame) -> np.ndarray:
        """
        Compute SHAP values for a batch of instances.
        
        Args:
            X: DataFrame of features.
            
        Returns:
            Array of SHAP values.
        """
        if not SHAP_AVAILABLE or self.explainer is None:
            raise RuntimeError("SHAP not available.")
        shap_values = self.explainer.shap_values(X)
        if isinstance(shap_values, list):
            return shap_values[0]
        return shap_values

    def get_summary_data(self, X: pd.DataFrame) -> Dict[str, Any]:
        """
        Get data required for a SHAP summary plot.
        
        Args:
            X: DataFrame of features to compute summary for.
            
        Returns:
            Dictionary with shap_values array and feature names.
        """
        shap_values = self.explain_batch(X)
        return {
            "shap_values": shap_values,
            "features": X,
            "feature_names": list(X.columns)
        }

    def generate_natural_language_explanation(self, row: pd.DataFrame, shap_values: np.ndarray, feature_names: List[str]) -> str:
        """
        Generate a human-readable explanation based on SHAP values.
        
        Args:
            row: The feature values.
            shap_values: Array of SHAP values for this instance.
            feature_names: List of feature names.
            
        Returns:
            Natural language explanation string.
        """
        if len(shap_values.shape) > 1:
            shap_values = shap_values[0]
            
        total_impact = np.sum(shap_values)
        if total_impact > 0:
            overall = f"Energy consumption for this part is {abs(total_impact):.2f} units above expected."
        else:
            overall = f"Energy consumption for this part is {abs(total_impact):.2f} units below expected."
            
        # Find top 2 contributors
        impacts = [(name, val, row[name].iloc[0] if isinstance(row, pd.DataFrame) else row[name]) 
                   for name, val in zip(feature_names, shap_values)]
        impacts.sort(key=lambda x: abs(x[1]), reverse=True)
        
        top1 = impacts[0]
        top2 = impacts[1] if len(impacts) > 1 else None
        
        primary_str = f"The primary contributor is {top1[0]} ({top1[2]:.1f}, contributing {'+' if top1[1]>0 else ''}{top1[1]:.2f} units)"
        if top2:
            secondary_str = f", followed by {top2[0]} ({top2[2]:.1f}, contributing {'+' if top2[1]>0 else ''}{top2[1]:.2f} units)."
        else:
            secondary_str = "."
            
        return f"{overall} {primary_str}{secondary_str}"
