"""
EcoTwin What-If Simulator
===========================
Allows users to modify operational parameters and instantly estimate
the impact on energy, cost, CO₂, and production.

All outputs are clearly labeled as simulated/estimated.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import sys
sys.path.insert(0, r'C:\Users\saish\.gemini\antigravity\scratch\ecotwin')
from src.utils.constants import GRID_EMISSION_FACTOR, BASE_TARIFF_INR


@dataclass
class SimulationResult:
    """Result of a What-If simulation."""
    # Energy
    current_energy_kwh: float
    new_energy_kwh: float
    energy_delta_kwh: float
    energy_delta_pct: float
    # SEC
    current_sec: float
    new_sec: float
    sec_delta: float
    # Cost
    current_cost_inr: float
    new_cost_inr: float
    cost_saving_inr: float
    # CO₂
    current_co2_kg: float
    new_co2_kg: float
    co2_reduction_kg: float
    # Annualized (daily production × operating days)
    annual_cost_saving_inr: float
    annual_co2_reduction_kg: float
    # Production
    production_impact: str
    # Confidence
    confidence: float
    warnings: List[str] = field(default_factory=list)
    label: str = "SIMULATION — Estimated impact based on model predictions"
    # Parameters changed
    parameters_changed: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


class WhatIfSimulator:
    """
    Interactive What-If simulator for energy optimization scenarios.
    
    Allows users to modify operational parameters (temperature, speed,
    idle time, etc.) and see the predicted impact on energy, cost, CO₂.
    
    Usage:
        sim = WhatIfSimulator(predictor)
        result = sim.simulate(
            current_params={'torque_nm': 48, 'process_temp_k': 312, ...},
            modified_params={'torque_nm': 42, 'process_temp_k': 310},
        )
    """

    def __init__(
        self,
        predictor,
        tariff_inr: float = BASE_TARIFF_INR,
        emission_factor: float = GRID_EMISSION_FACTOR,
        daily_production: int = 800,
        operating_days: int = 300,
    ):
        """
        Args:
            predictor: Fitted EnergyPredictor instance
            tariff_inr: Electricity tariff (₹/kWh)
            emission_factor: Grid CO₂ factor (kg CO₂/kWh)
            daily_production: Average daily production (parts)
            operating_days: Annual operating days
        """
        self.predictor = predictor
        self.tariff = tariff_inr
        self.emission_factor = emission_factor
        self.daily_production = daily_production
        self.operating_days = operating_days

    def simulate(
        self,
        current_params: Dict[str, float],
        modified_params: Dict[str, float],
        daily_production: Optional[int] = None,
    ) -> SimulationResult:
        """
        Simulate the impact of changing operational parameters.
        
        Args:
            current_params: Current operating values for ALL features
            modified_params: Only the parameters being changed (subset)
            daily_production: Override default daily production
            
        Returns:
            SimulationResult with energy, cost, CO₂ deltas
        """
        prod = daily_production or self.daily_production
        warnings = []

        # Create current and modified feature vectors
        current_df = pd.DataFrame([current_params])
        modified_values = current_params.copy()
        modified_values.update(modified_params)
        modified_df = pd.DataFrame([modified_values])

        # Check for extrapolation
        if hasattr(self.predictor, 'check_extrapolation'):
            extrap = self.predictor.check_extrapolation(modified_df)
            if extrap['any_extrapolation'].any():
                extrap_cols = [c.replace('_extrapolation', '')
                              for c in extrap.columns
                              if c != 'any_extrapolation' and extrap[c].any()]
                warnings.append(
                    f"Parameters outside training range: {extrap_cols}. "
                    "Predictions may be less reliable."
                )

        # Predict energy for both scenarios
        current_energy = float(self.predictor.predict(current_df)[0])
        new_energy = float(self.predictor.predict(modified_df)[0])

        # Compute deltas
        energy_delta = new_energy - current_energy
        energy_delta_pct = (
            (energy_delta / current_energy * 100)
            if current_energy > 0 else 0.0
        )

        # Scale to daily production
        daily_current = current_energy * prod
        daily_new = new_energy * prod
        daily_saving = daily_current - daily_new

        # Cost
        cost_current = daily_current * self.tariff
        cost_new = daily_new * self.tariff
        cost_saving = cost_current - cost_new

        # CO₂
        co2_current = daily_current * self.emission_factor
        co2_new = daily_new * self.emission_factor
        co2_reduction = co2_current - co2_new

        # Confidence: starts at 95, reduces for extrapolation and large changes
        confidence = 95.0
        if warnings:
            confidence -= 20.0
        if abs(energy_delta_pct) > 30:
            confidence -= 15.0
            warnings.append("Large predicted change (>30%). Verify feasibility.")
        confidence = max(confidence, 30.0)

        # Production impact
        production_impact = "Maintained"
        if 'cycle_time_minutes' in modified_params:
            ct_change = (
                modified_params['cycle_time_minutes'] -
                current_params.get('cycle_time_minutes', 1)
            )
            if ct_change > 0:
                pct = ct_change / current_params.get('cycle_time_minutes', 1) * 100
                production_impact = f"Potentially reduced by ~{pct:.0f}%"
            elif ct_change < 0:
                production_impact = "Potentially increased"

        return SimulationResult(
            current_energy_kwh=round(current_energy, 6),
            new_energy_kwh=round(new_energy, 6),
            energy_delta_kwh=round(energy_delta, 6),
            energy_delta_pct=round(energy_delta_pct, 2),
            current_sec=round(current_energy, 6),
            new_sec=round(new_energy, 6),
            sec_delta=round(energy_delta, 6),
            current_cost_inr=round(cost_current, 2),
            new_cost_inr=round(cost_new, 2),
            cost_saving_inr=round(cost_saving, 2),
            current_co2_kg=round(co2_current, 3),
            new_co2_kg=round(co2_new, 3),
            co2_reduction_kg=round(co2_reduction, 3),
            annual_cost_saving_inr=round(cost_saving * self.operating_days, 2),
            annual_co2_reduction_kg=round(co2_reduction * self.operating_days, 2),
            production_impact=production_impact,
            confidence=round(confidence, 1),
            warnings=warnings,
            parameters_changed=modified_params,
        )

    def simulate_batch(
        self, scenarios: List[Dict]
    ) -> List[SimulationResult]:
        """
        Simulate multiple scenarios for comparison.
        
        Args:
            scenarios: List of dicts, each with 'name', 'current_params',
                      'modified_params', optional 'daily_production'
                      
        Returns:
            List of SimulationResults
        """
        results = []
        for scenario in scenarios:
            result = self.simulate(
                current_params=scenario['current_params'],
                modified_params=scenario['modified_params'],
                daily_production=scenario.get('daily_production'),
            )
            results.append(result)
        return results

    def estimate_annual_impact(
        self,
        energy_saving_per_part: float,
        daily_parts: Optional[int] = None,
    ) -> Dict:
        """
        Extrapolate per-part savings to annual impact.
        
        Args:
            energy_saving_per_part: kWh saved per part
            daily_parts: Parts per day (default: self.daily_production)
        """
        parts = daily_parts or self.daily_production
        daily_kwh = energy_saving_per_part * parts
        annual_kwh = daily_kwh * self.operating_days

        return {
            "energy_saving_per_part_kwh": round(energy_saving_per_part, 6),
            "daily_production": parts,
            "operating_days": self.operating_days,
            "daily_energy_saving_kwh": round(daily_kwh, 2),
            "annual_energy_saving_kwh": round(annual_kwh, 2),
            "annual_cost_saving_inr": round(annual_kwh * self.tariff, 2),
            "annual_co2_reduction_kg": round(annual_kwh * self.emission_factor, 2),
            "annual_co2_reduction_tonnes": round(
                annual_kwh * self.emission_factor / 1000, 3
            ),
            "label": "ESTIMATED — Extrapolation based on model predictions",
        }
