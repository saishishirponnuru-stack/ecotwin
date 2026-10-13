"""
Machine Digital Twin Service for EcoTwin.
Provides detailed operational stats, gauges, and historical telemetry per machine.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Machine, TelemetryReading, AnomalyEvent


class MachineService:
    @staticmethod
    def get_all_machines(db: Session) -> List[Dict[str, Any]]:
        """List all monitored manufacturing cells."""
        machines = db.query(Machine).all()
        result = []
        for m in machines:
            latest = (
                db.query(TelemetryReading)
                .filter(TelemetryReading.machine_id == m.id)
                .order_by(TelemetryReading.timestamp.desc())
                .first()
            )
            result.append({
                "id": m.id,
                "name": m.name,
                "model_type": m.model_type,
                "rated_power_kw": m.rated_power_kw,
                "status": m.status,
                "latest_reading": latest.to_dict() if latest else None,
            })
        return result

    @staticmethod
    def get_machine_details(db: Session, machine_id: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Detailed operational profile, gauges, and recent telemetry."""
        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        if not machine:
            return None

        # Aggregate stats
        stats = db.query(
            func.count(TelemetryReading.id).label("total_readings"),
            func.avg(TelemetryReading.sec_kwh_per_part).label("avg_sec"),
            func.avg(TelemetryReading.rotational_speed_rpm).label("avg_speed"),
            func.avg(TelemetryReading.torque_nm).label("avg_torque"),
            func.max(TelemetryReading.tool_wear_min).label("max_wear"),
            func.avg(TelemetryReading.power_watts).label("avg_power"),
            func.avg(TelemetryReading.temp_diff_k).label("avg_temp_diff"),
        ).filter(TelemetryReading.machine_id == machine_id).first()

        recent_readings = (
            db.query(TelemetryReading)
            .filter(TelemetryReading.machine_id == machine_id)
            .order_by(TelemetryReading.timestamp.desc())
            .limit(limit)
            .all()
        )

        anomalies = (
            db.query(AnomalyEvent)
            .filter(AnomalyEvent.machine_id == machine_id)
            .order_by(AnomalyEvent.timestamp.desc())
            .limit(20)
            .all()
        )

        # Health score calculation
        total_r = stats.total_readings or 0
        anom_count = len(anomalies)
        max_wear = float(stats.max_wear or 0.0)
        
        wear_penalty = min(20.0, (max_wear / 250.0) * 20.0)
        health_score = max(40.0, min(100.0, 100.0 - (anom_count * 2.5) - wear_penalty))

        operating_stats = {
            "total_cycles_recorded": total_r,
            "health_score": round(health_score, 1),
            "avg_sec_kwh_per_part": round(float(stats.avg_sec or 0.0), 4),
            "avg_spindle_speed_rpm": round(float(stats.avg_speed or 0.0), 1),
            "avg_spindle_torque_nm": round(float(stats.avg_torque or 0.0), 1),
            "max_tool_wear_min": round(max_wear, 1),
            "avg_power_watts": round(float(stats.avg_power or 0.0), 1),
            "avg_temp_diff_k": round(float(stats.avg_temp_diff or 0.0), 2),
            "active_anomalies_count": anom_count,
            "tool_wear_status": "Overdue" if max_wear > 200 else ("Due" if max_wear > 150 else "Nominal"),
        }

        return {
            "machine": machine.to_dict(),
            "operating_stats": operating_stats,
            "recent_readings": [r.to_dict() for r in recent_readings],
            "active_anomalies": [a.to_dict() for a in anomalies],
        }
