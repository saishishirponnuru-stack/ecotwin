"""
Diagnostic Reason Codes Engine for EcoTwin.
"""
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
import pandas as pd

@dataclass
class DiagnosticReport:
    summary: str
    contributors: List[Dict[str, Any]]
    recommended_actions: List[Dict[str, Any]]
    historical_comparison: str


class DiagnosticEngine:
    """
    Generates diagnostic reports based on feature values and anomalies.
    """
    
    def __init__(self):
        pass

    def diagnose(self, row: pd.Series, residual_info: Dict[str, Any], shap_explanation: Optional[Dict[str, Any]] = None) -> DiagnosticReport:
        """
        Diagnose the cause of energy anomalies.
        
        Args:
            row: The raw/processed features for the instance.
            residual_info: Dictionary containing residual/anomaly data.
            shap_explanation: Optional SHAP explanation dictionary.
            
        Returns:
            DiagnosticReport with findings and recommendations.
        """
        contributors = []
        actions = []
        
        # 1. Tool wear check
        tool_wear = row.get("Tool wear [min]", 0)
        if tool_wear > 200:
            contributors.append({
                "factor": "Tool Wear",
                "description": f"Critical tool wear ({tool_wear} min).",
                "confidence": "High",
                "direction": "Increase"
            })
            actions.append({
                "action": "Replace tool",
                "reason": "Tool wear exceeds critical threshold, likely causing inefficiency.",
                "priority": "High",
                "estimated_impact": "Significant"
            })
        elif tool_wear > 150:
            contributors.append({
                "factor": "Tool Wear",
                "description": f"Moderate tool wear ({tool_wear} min).",
                "confidence": "Medium",
                "direction": "Increase"
            })
            actions.append({
                "action": "Schedule tool inspection",
                "reason": "Tool wear is elevated and may be contributing to energy loss.",
                "priority": "Medium",
                "estimated_impact": "Moderate"
            })
            
        # 2. Temperature deviation check
        air_temp = row.get("Air temperature [K]", None)
        process_temp = row.get("Process temperature [K]", None)
        if air_temp is not None and process_temp is not None:
            temp_diff = process_temp - air_temp
            if temp_diff > 15:
                contributors.append({
                    "factor": "Temperature Gradient",
                    "description": f"Unusually high temperature gradient ({temp_diff:.1f} K).",
                    "confidence": "Medium",
                    "direction": "Increase"
                })
                actions.append({
                    "action": "Inspect cooling system",
                    "reason": "Elevated process temperature relative to ambient.",
                    "priority": "Medium",
                    "estimated_impact": "Moderate"
                })

        # 3. Torque anomaly check
        torque = row.get("Torque [Nm]", None)
        if torque is not None and torque > 60:
             contributors.append({
                "factor": "High Torque",
                "description": f"Unusually high torque ({torque} Nm).",
                "confidence": "High",
                "direction": "Increase"
             })
             actions.append({
                 "action": "Check lubrication and material hardness",
                 "reason": "High torque indicates excessive resistance.",
                 "priority": "High",
                 "estimated_impact": "High"
             })

        summary = "Energy consumption anomaly detected. "
        if contributors:
            factors = [c["factor"] for c in contributors]
            summary += f"Possible contributors include: {', '.join(factors)}."
        else:
            summary += "No definitive contributors identified. Recommend general inspection."
            
        hist_comp = "Current operating parameters indicate a deviation from baseline behavior. "
        if residual_info.get("is_anomaly"):
             hist_comp += "This instance is flagged as a statistical anomaly based on historical data."
             
        return DiagnosticReport(
            summary=summary,
            contributors=contributors,
            recommended_actions=actions,
            historical_comparison=hist_comp
        )
