"""
Equipment Intelligence Module for EcoTwin.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List

class EquipmentIntelligence:
    """
    Computes per-machine metrics and fleet-wide summaries based on operational data.
    """
    
    def __init__(self, data: pd.DataFrame):
        """
        Initialize with the processed DataFrame containing anomaly detection results.
        
        Args:
            data: DataFrame containing features, machine IDs (UDI or derived), 
                  energy consumption, and anomaly flags.
        """
        self.data = data
        # Assume UDI is a proxy for machine/part or we have a 'Machine_ID' column
        self.machine_col = 'Machine_ID' if 'Machine_ID' in self.data.columns else 'UDI'

    def get_machine_profile(self, machine_id: Any) -> Dict[str, Any]:
        """
        Get the profile and metrics for a specific machine.
        
        Args:
            machine_id: The identifier for the machine.
            
        Returns:
            Dictionary containing health score, efficiency, trend, etc.
        """
        m_data = self.data[self.data[self.machine_col] == machine_id]
        if m_data.empty:
            return {"error": f"Machine {machine_id} not found."}
            
        # Calculate total anomalies
        anomaly_col = 'is_anomaly' if 'is_anomaly' in m_data.columns else 'Machine failure'
        total_anomalies = m_data[anomaly_col].sum() if anomaly_col in m_data.columns else 0
        
        # Average deviation (if residual is available)
        avg_dev = m_data['residual'].mean() if 'residual' in m_data.columns else 0
        
        # Mock health score based on anomalies
        health_score = max(0, 100 - (total_anomalies * 5))
        
        # Tool wear max
        max_wear = m_data['Tool wear [min]'].max() if 'Tool wear [min]' in m_data.columns else 0
        
        # Maintenance risk
        maintenance_risk = min(100, (max_wear / 250.0) * 100) if max_wear > 0 else 0
        
        # SEC (Specific Energy Consumption) pseudo-calculation
        # Using torque * rpm as a proxy for power
        if 'Torque [Nm]' in m_data.columns and 'Rotational speed [rpm]' in m_data.columns:
            power = m_data['Torque [Nm]'] * m_data['Rotational speed [rpm]'] * (2 * np.pi / 60)
            avg_sec = power.mean()
        else:
            avg_sec = 0
            
        # Trend (mock implementation)
        trend = "Stable"
        if len(m_data) > 7:
             recent_sec = power.iloc[-7:].mean() if 'power' in locals() else 0
             if recent_sec > avg_sec * 1.05:
                 trend = "Degrading"
             elif recent_sec < avg_sec * 0.95:
                 trend = "Improving"
                 
        return {
            "machine_id": machine_id,
            "health_score": float(health_score),
            "average_sec": float(avg_sec),
            "trend": trend,
            "total_anomalies": int(total_anomalies),
            "maintenance_risk_score": float(maintenance_risk),
            "potential_savings": float(avg_dev * 0.1) if avg_dev > 0 else 0.0
        }

    def get_fleet_summary(self) -> pd.DataFrame:
        """
        Get a summary ranking of all machines.
        
        Returns:
            DataFrame with fleet metrics.
        """
        machine_ids = self.data[self.machine_col].unique()
        profiles = [self.get_machine_profile(mid) for mid in machine_ids[:100]] # Limit for performance if many
        
        df = pd.DataFrame([p for p in profiles if "error" not in p])
        if not df.empty:
            df = df.sort_values(by="health_score", ascending=False)
        return df

    def get_maintenance_priority(self) -> List[Dict[str, Any]]:
        """
        Get list of machines sorted by maintenance urgency.
        
        Returns:
            List of machine profiles, sorted by maintenance risk.
        """
        summary_df = self.get_fleet_summary()
        if summary_df.empty:
            return []
            
        urgent = summary_df.sort_values(by="maintenance_risk_score", ascending=False)
        return urgent.to_dict(orient="records")
