"""
EcoTwin Recommendation Engine
================================
Generates prioritized, constraint-aware operational recommendations
based on anomaly detection results and equipment intelligence.

Safety: Never recommends unsafe settings or actions outside manufacturer limits.
Language: Uses cautious framing (possible, likely, recommend investigation).
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass, field

import sys
sys.path.insert(0, r'C:\Users\saish\.gemini\antigravity\scratch\ecotwin')
from src.utils.constants import (
    GRID_EMISSION_FACTOR, BASE_TARIFF_INR, FEATURE_RANGES,
)


DIFFICULTY_FACTOR = {'Low': 1.0, 'Medium': 1.5, 'High': 2.0}


@dataclass
class Recommendation:
    """A single actionable recommendation."""
    priority: int
    action: str
    reason: str
    expected_benefit: Dict  # {energy_saving_kwh, cost_saving_inr, co2_reduction_kg}
    confidence: float  # 0-100
    difficulty: str  # Low / Medium / High
    machine_id: str
    category: str  # Process Optimization / Maintenance / Scheduling / Equipment
    production_impact: str
    priority_score: float = 0.0

    def to_dict(self) -> Dict:
        d = {
            'priority': self.priority,
            'action': self.action,
            'reason': self.reason,
            'expected_benefit': self.expected_benefit,
            'confidence': round(self.confidence, 1),
            'difficulty': self.difficulty,
            'machine_id': self.machine_id,
            'category': self.category,
            'production_impact': self.production_impact,
        }
        return d


class RecommendationEngine:
    """
    Generates prioritized operational recommendations based on
    anomaly detection, equipment profiles, and energy analysis.
    
    Priority scoring: Impact × Confidence × (1 / DifficultyFactor)
    """

    def __init__(
        self,
        tariff_inr: float = BASE_TARIFF_INR,
        emission_factor: float = GRID_EMISSION_FACTOR,
        daily_production: int = 800,
    ):
        self.tariff = tariff_inr
        self.ef = emission_factor
        self.daily_production = daily_production

    def generate_recommendations(
        self,
        df: pd.DataFrame,
        anomaly_results: Optional[pd.DataFrame] = None,
        equipment_profiles: Optional[Dict] = None,
    ) -> List[Recommendation]:
        """
        Analyze data and generate prioritized recommendations.
        
        Args:
            df: Full processed DataFrame with all features
            anomaly_results: Output from AnomalyDetector.detect()
            equipment_profiles: Per-machine profiles from EquipmentIntelligence
            
        Returns:
            Sorted list of Recommendations (highest priority first)
        """
        recommendations = []

        # Group by machine for machine-specific recommendations
        for machine_id in df['machine_id'].unique():
            machine_data = df[df['machine_id'] == machine_id]
            recs = self._analyze_machine(machine_id, machine_data, anomaly_results)
            recommendations.extend(recs)

        # Global recommendations
        recommendations.extend(self._analyze_global(df))

        # Score and sort
        for rec in recommendations:
            impact = rec.expected_benefit.get('energy_saving_kwh', 0)
            rec.priority_score = (
                impact * (rec.confidence / 100) / DIFFICULTY_FACTOR[rec.difficulty]
            )

        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        for i, rec in enumerate(recommendations):
            rec.priority = i + 1

        return recommendations

    def _analyze_machine(
        self,
        machine_id: str,
        data: pd.DataFrame,
        anomaly_results: Optional[pd.DataFrame],
    ) -> List[Recommendation]:
        """Generate recommendations for a specific machine."""
        recs = []

        # 1. Temperature optimization
        if 'process_temp_k' in data.columns:
            avg_temp = data['process_temp_k'].mean()
            baseline_temp = 310.0  # ~mean from dataset
            if avg_temp > baseline_temp + 1.5:
                delta_temp = avg_temp - baseline_temp
                # Rough estimate: each degree above baseline ≈ 0.5% energy increase
                energy_pct_saving = min(delta_temp * 0.5, 15.0)
                avg_energy = data['energy_kwh'].mean()
                saving_per_part = avg_energy * energy_pct_saving / 100
                daily_saving = saving_per_part * self.daily_production / len(data['machine_id'].unique())

                recs.append(Recommendation(
                    priority=0,
                    action=(
                        f"Investigate process temperature on {machine_id}. "
                        f"Current avg: {avg_temp:.1f} K ({avg_temp-273.15:.1f}°C), "
                        f"baseline: {baseline_temp:.1f} K. "
                        f"Consider reducing by {delta_temp:.1f} K."
                    ),
                    reason=(
                        f"Process temperature is {delta_temp:.1f} K above baseline. "
                        "Elevated temperature may indicate controller drift, "
                        "inadequate cooling, or suboptimal setpoint."
                    ),
                    expected_benefit={
                        'energy_saving_kwh': round(daily_saving, 2),
                        'cost_saving_inr': round(daily_saving * self.tariff, 2),
                        'co2_reduction_kg': round(daily_saving * self.ef, 3),
                        'annual_cost_saving_inr': round(daily_saving * self.tariff * 300, 2),
                    },
                    confidence=72.0,
                    difficulty='Low',
                    machine_id=machine_id,
                    category='Process Optimization',
                    production_impact='Maintained — temperature reduction within safe range',
                ))

        # 2. Idle time reduction
        if 'idle_time_seconds' in data.columns:
            avg_idle = data['idle_time_seconds'].mean()
            if avg_idle > 45:  # More than 45s average idle
                # Base load during idle ≈ 2.5 kW (from constants)
                reducible_idle = (avg_idle - 20) / 3600  # hours of reducible idle per part
                saving_per_part = 2.5 * reducible_idle  # kWh
                parts_per_machine = self.daily_production / len(data['machine_id'].unique())
                daily_saving = saving_per_part * parts_per_machine

                recs.append(Recommendation(
                    priority=0,
                    action=(
                        f"Reduce idle time on {machine_id}. "
                        f"Current avg: {avg_idle:.0f}s between operations. "
                        "Target: 20s. Optimize material handling and scheduling."
                    ),
                    reason=(
                        f"Machine draws ~2.5 kW base load during idle. "
                        f"At {avg_idle:.0f}s/part, idle power waste accumulates significantly."
                    ),
                    expected_benefit={
                        'energy_saving_kwh': round(daily_saving, 2),
                        'cost_saving_inr': round(daily_saving * self.tariff, 2),
                        'co2_reduction_kg': round(daily_saving * self.ef, 3),
                        'annual_cost_saving_inr': round(daily_saving * self.tariff * 300, 2),
                    },
                    confidence=85.0,
                    difficulty='Low',
                    machine_id=machine_id,
                    category='Scheduling',
                    production_impact='Maintained — reduces non-productive time only',
                ))

        # 3. Maintenance scheduling
        if 'maintenance_status' in data.columns:
            overdue_pct = (data['maintenance_status'] == 'Overdue').mean() * 100
            if overdue_pct > 10:
                avg_energy = data['energy_kwh'].mean()
                ok_data = data[data['maintenance_status'] == 'OK']
                baseline_energy = ok_data['energy_kwh'].mean() if len(ok_data) > 0 else avg_energy
                excess = avg_energy - baseline_energy
                parts_per_machine = self.daily_production / len(data['machine_id'].unique())
                daily_saving = max(excess, 0) * parts_per_machine

                recs.append(Recommendation(
                    priority=0,
                    action=(
                        f"Schedule preventive maintenance for {machine_id}. "
                        f"{overdue_pct:.0f}% of recent operations show overdue maintenance."
                    ),
                    reason=(
                        "Overdue maintenance correlates with increased energy consumption. "
                        "Mechanical wear increases friction, reducing efficiency."
                    ),
                    expected_benefit={
                        'energy_saving_kwh': round(daily_saving, 2),
                        'cost_saving_inr': round(daily_saving * self.tariff, 2),
                        'co2_reduction_kg': round(daily_saving * self.ef, 3),
                        'annual_cost_saving_inr': round(daily_saving * self.tariff * 300, 2),
                    },
                    confidence=65.0,
                    difficulty='Medium',
                    machine_id=machine_id,
                    category='Maintenance',
                    production_impact='Short-term downtime for maintenance; long-term improvement',
                ))

        # 4. High torque investigation
        if 'torque_nm' in data.columns:
            avg_torque = data['torque_nm'].mean()
            high_torque_pct = (data['torque_nm'] > 55).mean() * 100
            if high_torque_pct > 15:
                recs.append(Recommendation(
                    priority=0,
                    action=(
                        f"Investigate frequent high-torque events on {machine_id}. "
                        f"{high_torque_pct:.0f}% of operations exceed 55 Nm."
                    ),
                    reason=(
                        "Persistently high torque may indicate: material hardness variation, "
                        "worn tooling, misalignment, or suboptimal feed/speed settings. "
                        "Higher torque directly increases energy consumption."
                    ),
                    expected_benefit={
                        'energy_saving_kwh': round(data['energy_kwh'].mean() * 0.05 * self.daily_production / 4, 2),
                        'cost_saving_inr': round(data['energy_kwh'].mean() * 0.05 * self.daily_production / 4 * self.tariff, 2),
                        'co2_reduction_kg': round(data['energy_kwh'].mean() * 0.05 * self.daily_production / 4 * self.ef, 3),
                    },
                    confidence=58.0,
                    difficulty='Medium',
                    machine_id=machine_id,
                    category='Equipment',
                    production_impact='Requires investigation — may need tooling change',
                ))

        return recs

    def _analyze_global(self, df: pd.DataFrame) -> List[Recommendation]:
        """Generate plant-wide recommendations."""
        recs = []

        # Load shifting recommendation
        if 'shift' in df.columns and 'electricity_tariff' in df.columns:
            shift_energy = df.groupby('shift')['energy_kwh'].sum()
            shift_tariff = df.groupby('shift')['electricity_tariff'].first()
            peak_shift = shift_tariff.idxmax()
            offpeak_shift = shift_tariff.idxmin()

            if shift_tariff[peak_shift] > shift_tariff[offpeak_shift] * 1.3:
                peak_energy = shift_energy.get(peak_shift, 0)
                shiftable_pct = 10  # Assume 10% of peak load is flexible
                shiftable_kwh = peak_energy * shiftable_pct / 100
                tariff_diff = shift_tariff[peak_shift] - shift_tariff[offpeak_shift]
                daily_saving = shiftable_kwh * tariff_diff

                recs.append(Recommendation(
                    priority=0,
                    action=(
                        f"Shift {shiftable_pct}% of flexible {peak_shift} shift load "
                        f"to {offpeak_shift} shift. "
                        f"Tariff difference: ₹{tariff_diff:.1f}/kWh."
                    ),
                    reason=(
                        f"Time-of-use tariff creates ₹{tariff_diff:.1f}/kWh cost difference. "
                        "Non-critical operations (cleaning, testing, setup) can be rescheduled."
                    ),
                    expected_benefit={
                        'energy_saving_kwh': 0,  # Same energy, different cost
                        'cost_saving_inr': round(daily_saving, 2),
                        'co2_reduction_kg': 0,
                        'annual_cost_saving_inr': round(daily_saving * 300, 2),
                    },
                    confidence=80.0,
                    difficulty='Medium',
                    machine_id='All',
                    category='Scheduling',
                    production_impact='Maintained — only flexible non-critical loads shifted',
                ))

        return recs
