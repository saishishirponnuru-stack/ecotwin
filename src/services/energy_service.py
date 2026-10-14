from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Machine, TelemetryReading, SystemSetting
from src.services.overview_service import OverviewService
from src.utils.constants import GRID_EMISSION_FACTOR, BASE_TARIFF_INR

class EnergyService:
    """Service layer for Energy Intelligence calculations."""

    @staticmethod
    def get_executive_overview(db: Session) -> Dict[str, Any]:
        """Return overview with additional cost and CO₂ metrics.
        Reuses OverviewService for base KPIs then augments with
        calculated `cost_inr` and `co2_tonnes` derived from total energy.
        """
        base = OverviewService.get_executive_overview(db)
        # Compute cost and CO₂ based on total energy if present
        total_energy = base.get("total_energy_kwh", 0.0)
        tariff_setting = db.query(SystemSetting).filter_by(key="base_tariff_inr").first()
        emission_setting = db.query(SystemSetting).filter_by(key="grid_emission_factor").first()
        tariff = float(tariff_setting.value) if tariff_setting else BASE_TARIFF_INR
        emission_factor = float(emission_setting.value) if emission_setting else GRID_EMISSION_FACTOR
        base["cost_inr"] = round(total_energy * tariff, 0)
        base["co2_tonnes"] = round(total_energy * emission_factor / 1000.0, 2)
        return base

    @staticmethod
    def get_machine_comparison(db: Session) -> List[Dict[str, Any]]:
        """Return per‑machine energy intensity and derived cost/CO₂.
        Each entry contains:
          - machine_id
          - avg_sec_kwh_per_part
          - total_energy_kwh
          - cost_inr (energy * tariff)
          - co2_tonnes (energy * emission factor / 1000)
        """
        results: List[Dict[str, Any]] = []
        tariff_setting = db.query(SystemSetting).filter_by(key="base_tariff_inr").first()
        emission_setting = db.query(SystemSetting).filter_by(key="grid_emission_factor").first()
        tariff = float(tariff_setting.value) if tariff_setting else BASE_TARIFF_INR
        emission_factor = float(emission_setting.value) if emission_setting else GRID_EMISSION_FACTOR
        machines = db.query(Machine).all()
        for m in machines:
            stats = db.query(
                func.sum(TelemetryReading.energy_kwh).label("total_energy"),
                func.avg(TelemetryReading.sec_kwh_per_part).label("avg_sec"),
                func.count(TelemetryReading.id).label("count"),
            ).filter(TelemetryReading.machine_id == m.id).first()
            total_energy = float(stats.total_energy or 0.0)
            avg_sec = float(stats.avg_sec or 0.0)
            cost = total_energy * tariff
            co2 = total_energy * emission_factor / 1000.0
            results.append({
                "machine_id": m.id,
                "machine_name": m.name,
                "avg_sec_kwh_per_part": round(avg_sec, 4),
                "total_energy_kwh": round(total_energy, 2),
                "cost_inr": round(cost, 0),
                "co2_tonnes": round(co2, 2),
            })
        return results
