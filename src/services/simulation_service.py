"""
What-If Optimization & Simulation Service for EcoTwin.
Enforces coupled physical relationships (kinematics, tool wear reset, idle standby)
and evaluates standardized Out-Of-Distribution (OOD) distance.
"""

from typing import Dict, Any, List, Optional
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Machine, TelemetryReading, SimulationScenario, SystemSetting
from src.utils.constants import (
    GRID_EMISSION_FACTOR,
    BASE_TARIFF_INR,
    FEATURE_RANGES,
    TOU_SCHEDULE,
)


class SimulationService:
    @staticmethod
    def simulate(
        db: Session,
        machine_id: str,
        spindle_speed_rpm: Optional[float] = None,
        torque_nm: Optional[float] = None,
        tool_replacement: bool = False,
        idle_cutoff_seconds: Optional[float] = None,
        shift_reschedule: Optional[str] = None,
        daily_production: int = 800,
    ) -> Dict[str, Any]:
        """
        Runs a physics-grounded What-If simulation with coupled variables.
        """
        if not db.get(Machine, machine_id):
            raise ValueError(f"Machine '{machine_id}' not found")
        # 1. Fetch Machine Baseline Values
        base_stats = db.query(
            func.avg(TelemetryReading.rotational_speed_rpm).label("speed"),
            func.avg(TelemetryReading.torque_nm).label("torque"),
            func.avg(TelemetryReading.cycle_time_minutes).label("cycle_time"),
            func.avg(TelemetryReading.tool_wear_min).label("wear"),
            func.avg(TelemetryReading.idle_time_seconds).label("idle"),
            func.avg(TelemetryReading.energy_kwh).label("energy"),
            func.count(TelemetryReading.id).label("reading_count"),
        ).filter(TelemetryReading.machine_id == machine_id).first()

        if not base_stats.reading_count:
            raise ValueError(f"Machine '{machine_id}' has no telemetry available for simulation")

        base_speed = float(base_stats.speed or 1500.0)
        base_torque = float(base_stats.torque or 40.0)
        base_cycle_time = float(base_stats.cycle_time or 3.0)
        base_wear = float(base_stats.wear or 100.0)
        base_idle = float(base_stats.idle or 25.0)
        base_energy = float(base_stats.energy or 0.369)

        # Fetch active tariff and emission factor
        grid_setting = db.query(SystemSetting).filter_by(key="grid_emission_factor").first()
        tariff_setting = db.query(SystemSetting).filter_by(key="base_tariff_inr").first()
        tariff = float(tariff_setting.value) if tariff_setting else BASE_TARIFF_INR
        emission_factor = float(grid_setting.value) if grid_setting else GRID_EMISSION_FACTOR

        warnings = []
        tradeoffs = {}

        # 2. Coupled Speed & Cycle Time Modification
        target_speed = spindle_speed_rpm if spindle_speed_rpm is not None else base_speed
        target_torque = torque_nm if torque_nm is not None else base_torque

        # Speed scaling affects cycle time inversely (higher speed -> lower cutting time)
        speed_ratio = target_speed / base_speed
        sim_cycle_time = base_cycle_time / speed_ratio
        tradeoffs["cycle_time_minutes"] = round(sim_cycle_time, 2)

        # 3. Mechanical Power & Electrical Power
        p_mech = target_torque * (target_speed * 2.0 * np.pi / 60.0)
        p_elec = p_mech / 0.85
        sim_cutting_energy = (p_elec * (sim_cycle_time / 60.0)) / 1000.0

        # 4. Tool Replacement Lever (friction reset)
        if tool_replacement:
            # Worn tool adds ~10% friction penalty. Replacement restores baseline efficiency.
            friction_reduction = 0.10 if base_wear > 120 else 0.05
            sim_cutting_energy *= (1.0 - friction_reduction)
            tradeoffs["tool_wear_friction_saved_pct"] = round(friction_reduction * 100, 1)

        # 5. Idle Standby Cutoff Lever
        sim_idle = idle_cutoff_seconds if idle_cutoff_seconds is not None else base_idle
        aux_power_w = 1200.0  # 1.2 kW auxiliary standby draw
        idle_delta_s = max(0.0, base_idle - sim_idle)
        idle_energy_saved_kwh = (aux_power_w * (idle_delta_s / 3600.0)) / 1000.0
        tradeoffs["idle_standby_saved_kwh_per_part"] = round(idle_energy_saved_kwh, 6)

        sim_energy = max(0.05, sim_cutting_energy - idle_energy_saved_kwh)

        # 6. Shift Rescheduling (Tariff impact)
        tariff_multiplier = 1.0
        if shift_reschedule:
            shift_upper = shift_reschedule.upper()
            if shift_upper in ["NIGHT", "OFFPEAK"]:
                tariff_multiplier = 0.80
                tradeoffs["tariff_tier"] = "Off-Peak Night (-20% rate)"
            elif shift_upper in ["EVENING", "PEAK"]:
                tariff_multiplier = 1.20
                tradeoffs["tariff_tier"] = "Peak Evening (+20% surcharge)"
            else:
                tradeoffs["tariff_tier"] = "Normal Daytime (Base rate)"

        effective_tariff = tariff * tariff_multiplier

        # 7. Energy Deltas and Financial Savings
        delta_kwh = sim_energy - base_energy
        delta_pct = (delta_kwh / base_energy * 100.0) if base_energy > 0 else 0.0

        daily_saving_kwh = -delta_kwh * daily_production
        annual_cost_saving = daily_saving_kwh * effective_tariff * 300.0
        annual_co2_saving = daily_saving_kwh * emission_factor * 300.0

        # 8. Standardized OOD Distance Calculation
        # Normalized distance from empirical operating bounds
        speed_norm = abs(target_speed - 1500.0) / 300.0
        torque_norm = abs(target_torque - 40.0) / 10.0
        ood_distance = round(float(max(speed_norm, torque_norm)), 2)

        if ood_distance <= 2.0:
            reliability = "Interpolation (High)"
        elif ood_distance <= 3.5:
            reliability = "Mild Extrapolation (Caution)"
            warnings.append(f"Operating parameters are near boundary (OOD score: {ood_distance}). Verify physical tooling.")
        else:
            reliability = "OOD (Unsupported)"
            warnings.append(f"Operating parameters exceed supported machine envelope (OOD score: {ood_distance}). High risk of tool failure.")

        return {
            "baseline_energy_kwh": round(base_energy, 6),
            "simulated_energy_kwh": round(sim_energy, 6),
            "delta_energy_kwh": round(delta_kwh, 6),
            "delta_pct": round(delta_pct, 2),
            "daily_saving_kwh": round(daily_saving_kwh, 2),
            "annual_cost_saving_inr": round(annual_cost_saving, 0),
            "annual_co2_reduction_kg": round(annual_co2_saving, 1),
            "ood_distance": ood_distance,
            "reliability_status": reliability,
            "warnings": warnings,
            "physical_tradeoffs": tradeoffs,
            "label": "SIMULATION — Physics & Empirical Estimate",
        }

    @staticmethod
    def save_scenario(db: Session, name: str, machine_id: str, parameters_in: Dict, result_out: Dict) -> Dict[str, Any]:
        """Save a What-If scenario to the database."""
        scenario = SimulationScenario(
            name=name,
            machine_id=machine_id,
            parameters_in=parameters_in,
            result_out=result_out,
        )
        db.add(scenario)
        db.commit()
        db.refresh(scenario)
        return scenario.to_dict()

    @staticmethod
    def list_scenarios(db: Session, machine_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List saved scenarios."""
        q = db.query(SimulationScenario)
        if machine_id:
            q = q.filter(SimulationScenario.machine_id == machine_id)
        scenarios = q.order_by(SimulationScenario.created_at.desc()).all()
        return [s.to_dict() for s in scenarios]
