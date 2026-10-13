"""
EcoTwin Impact Calculator
==========================
Computes energy, cost, CO₂, and SEC impact of operational changes.
All results clearly labeled as estimates.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional

import sys
sys.path.insert(0, r'C:\Users\saish\.gemini\antigravity\scratch\ecotwin')
from src.utils.constants import GRID_EMISSION_FACTOR, BASE_TARIFF_INR


@dataclass
class BeforeAfterReport:
    """Structured before/after comparison for dashboard display."""
    # Before state
    before_energy_kwh: float
    before_sec_kwh_per_part: float
    before_cost_inr: float
    before_co2_kg: float
    before_production_units: int
    # After state
    after_energy_kwh: float
    after_sec_kwh_per_part: float
    after_cost_inr: float
    after_co2_kg: float
    after_production_units: int
    # Deltas
    energy_reduction_kwh: float
    energy_reduction_pct: float
    sec_reduction_kwh: float
    sec_reduction_pct: float
    cost_saving_inr: float
    cost_saving_pct: float
    co2_reduction_kg: float
    co2_reduction_pct: float
    production_change_pct: float
    # Annualized
    annual_cost_saving_inr: float
    annual_co2_reduction_kg: float
    annual_co2_reduction_tonnes: float
    # Meta
    operating_days: int = 300
    label: str = "ESTIMATED — Based on model predictions"

    def to_dict(self) -> Dict:
        return {k: round(v, 2) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


class ImpactCalculator:
    """
    Computes measurable impact of energy optimization actions.
    
    All outputs are clearly labeled as estimates based on model predictions.
    Uses configurable tariff and emission factors.
    """

    def __init__(
        self,
        tariff_inr: float = BASE_TARIFF_INR,
        emission_factor: float = GRID_EMISSION_FACTOR,
    ):
        self.tariff_inr = tariff_inr
        self.emission_factor = emission_factor

    def compute_energy_impact(
        self, actual_kwh: float, optimized_kwh: float
    ) -> Dict:
        """Compute energy savings."""
        saving = actual_kwh - optimized_kwh
        pct = (saving / actual_kwh * 100) if actual_kwh > 0 else 0.0
        return {
            "actual_kwh": round(actual_kwh, 4),
            "optimized_kwh": round(optimized_kwh, 4),
            "saving_kwh": round(saving, 4),
            "saving_pct": round(pct, 2),
        }

    def compute_cost_impact(
        self, energy_saving_kwh: float, tariff: Optional[float] = None
    ) -> Dict:
        """Compute cost savings (daily, monthly, annual)."""
        t = tariff or self.tariff_inr
        daily = energy_saving_kwh * t
        return {
            "tariff_inr_per_kwh": t,
            "daily_saving_inr": round(daily, 2),
            "monthly_saving_inr": round(daily * 26, 2),  # 26 working days
            "annual_saving_inr": round(daily * 300, 2),   # 300 operating days
        }

    def compute_co2_impact(
        self, energy_saving_kwh: float, ef: Optional[float] = None
    ) -> Dict:
        """Compute CO₂ reduction."""
        factor = ef or self.emission_factor
        kg = energy_saving_kwh * factor
        return {
            "emission_factor_kg_per_kwh": factor,
            "source": "CEA India CO₂ Baseline Database v19",
            "daily_reduction_kg": round(kg, 3),
            "monthly_reduction_kg": round(kg * 26, 2),
            "annual_reduction_kg": round(kg * 300, 2),
            "annual_reduction_tonnes": round(kg * 300 / 1000, 3),
        }

    def compute_sec_impact(
        self, current_sec: float, optimized_sec: float
    ) -> Dict:
        """Compute specific energy consumption improvement."""
        reduction = current_sec - optimized_sec
        pct = (reduction / current_sec * 100) if current_sec > 0 else 0.0
        return {
            "current_sec_kwh_per_part": round(current_sec, 4),
            "optimized_sec_kwh_per_part": round(optimized_sec, 4),
            "reduction_kwh_per_part": round(reduction, 4),
            "reduction_pct": round(pct, 2),
        }

    def compute_before_after(
        self,
        current_energy_per_part: float,
        optimized_energy_per_part: float,
        daily_production: int,
        operating_days: int = 300,
        tariff: Optional[float] = None,
        ef: Optional[float] = None,
    ) -> BeforeAfterReport:
        """
        Compute complete before/after comparison.
        
        Args:
            current_energy_per_part: Current SEC (kWh/part)
            optimized_energy_per_part: Projected optimized SEC (kWh/part)
            daily_production: Parts produced per day
            operating_days: Working days per year
            tariff: Electricity tariff (₹/kWh)
            ef: Grid emission factor (kg CO₂/kWh)
        """
        t = tariff or self.tariff_inr
        factor = ef or self.emission_factor

        before_energy = current_energy_per_part * daily_production
        after_energy = optimized_energy_per_part * daily_production

        before_cost = before_energy * t
        after_cost = after_energy * t

        before_co2 = before_energy * factor
        after_co2 = after_energy * factor

        e_reduction = before_energy - after_energy
        e_pct = (e_reduction / before_energy * 100) if before_energy > 0 else 0

        sec_red = current_energy_per_part - optimized_energy_per_part
        sec_pct = (sec_red / current_energy_per_part * 100) if current_energy_per_part > 0 else 0

        cost_saving = before_cost - after_cost
        cost_pct = (cost_saving / before_cost * 100) if before_cost > 0 else 0

        co2_red = before_co2 - after_co2
        co2_pct = (co2_red / before_co2 * 100) if before_co2 > 0 else 0

        return BeforeAfterReport(
            before_energy_kwh=round(before_energy, 2),
            before_sec_kwh_per_part=round(current_energy_per_part, 4),
            before_cost_inr=round(before_cost, 2),
            before_co2_kg=round(before_co2, 2),
            before_production_units=daily_production,
            after_energy_kwh=round(after_energy, 2),
            after_sec_kwh_per_part=round(optimized_energy_per_part, 4),
            after_cost_inr=round(after_cost, 2),
            after_co2_kg=round(after_co2, 2),
            after_production_units=daily_production,
            energy_reduction_kwh=round(e_reduction, 2),
            energy_reduction_pct=round(e_pct, 1),
            sec_reduction_kwh=round(sec_red, 4),
            sec_reduction_pct=round(sec_pct, 1),
            cost_saving_inr=round(cost_saving, 2),
            cost_saving_pct=round(cost_pct, 1),
            co2_reduction_kg=round(co2_red, 2),
            co2_reduction_pct=round(co2_pct, 1),
            production_change_pct=0.0,
            annual_cost_saving_inr=round(cost_saving * operating_days, 2),
            annual_co2_reduction_kg=round(co2_red * operating_days, 2),
            annual_co2_reduction_tonnes=round(co2_red * operating_days / 1000, 3),
            operating_days=operating_days,
        )
