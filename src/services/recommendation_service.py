"""
Recommendation Service.
Provides deterministic, data-driven recommendation generation for the EcoTwin facility.
All returned fields conform to the RecommendationItem schema in src.schemas.
"""

from typing import List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.db.models import Machine, TelemetryReading, AnomalyEvent


class RecommendationService:
    @staticmethod
    def _machine_stats(db: Session, machine_id: str) -> Dict[str, Any]:
        """Aggregate telemetry and anomaly data for a single machine."""
        telemetry = db.query(
            func.avg(TelemetryReading.sec_kwh_per_part).label('avg_sec'),
            func.sum(TelemetryReading.energy_kwh).label('total_energy'),
            func.count(TelemetryReading.id).label('reading_count'),
        ).filter(TelemetryReading.machine_id == machine_id).first()
        avg_sec = float(telemetry.avg_sec or 0.0)
        total_energy = float(telemetry.total_energy or 0.0)
        anomaly_count = db.query(AnomalyEvent).filter(
            AnomalyEvent.machine_id == machine_id
        ).count()
        return {
            'avg_sec': avg_sec,
            'total_energy': total_energy,
            'reading_count': int(telemetry.reading_count or 0),
            'anomaly_count': anomaly_count,
        }

    @staticmethod
    def generate_all(db: Session) -> List[Dict[str, Any]]:
        """
        Generate a list of recommendation dicts for the whole facility.
        Rules:
        1. High energy: machine total_energy > 1.2x facility per-machine average.
        2. Low efficiency: avg_sec > 1.15x facility avg_sec.
        3. Frequent anomalies: anomaly_count > 5.
        """
        facility_stats = db.query(
            func.avg(TelemetryReading.sec_kwh_per_part).label('facility_avg_sec'),
            func.sum(TelemetryReading.energy_kwh).label('facility_total_energy')
        ).first()
        fac_avg_sec = float(facility_stats.facility_avg_sec or 0.0)
        fac_total_energy = float(facility_stats.facility_total_energy or 0.0)
        machines = db.query(Machine).all()
        telemetry_by_machine = {
            row.machine_id: row
            for row in db.query(
                TelemetryReading.machine_id,
                func.avg(TelemetryReading.sec_kwh_per_part).label("avg_sec"),
                func.sum(TelemetryReading.energy_kwh).label("total_energy"),
                func.count(TelemetryReading.id).label("reading_count"),
            ).group_by(TelemetryReading.machine_id).all()
        }
        anomalies_by_machine = {
            row.machine_id: row.anomaly_count
            for row in db.query(
                AnomalyEvent.machine_id,
                func.count(AnomalyEvent.id).label("anomaly_count"),
            ).group_by(AnomalyEvent.machine_id).all()
        }
        recommendations: List[Dict[str, Any]] = []
        rec_id = 1
        n_machines = max(len(machines), 1)
        for m in machines:
            telemetry = telemetry_by_machine.get(m.id)
            stats = {
                "avg_sec": float(telemetry.avg_sec or 0.0) if telemetry else 0.0,
                "total_energy": float(telemetry.total_energy or 0.0) if telemetry else 0.0,
                "reading_count": int(telemetry.reading_count or 0) if telemetry else 0,
                "anomaly_count": anomalies_by_machine.get(m.id, 0),
            }
            # Rule 1: High total energy
            if fac_total_energy > 0 and stats['total_energy'] > 1.2 * (fac_total_energy / n_machines):
                recommendations.append({
                    'id': rec_id,
                    'machine_id': m.id,
                    'category': 'Energy Consumption',
                    'action': 'Review operating schedule and idle periods.',
                    'reason': (
                        f"Machine consumes {stats['total_energy']:.1f} kWh, "
                        f">20% above facility average."
                    ),
                    'expected_benefit': {},
                    'difficulty': 'Medium',
                    'evidence_source': 'Telemetry aggregation',
                    'evidence_summary': (
                        f"{stats['reading_count']} telemetry readings; total energy is more than "
                        "20% above the facility per-machine average."
                    ),
                    'provenance': 'TIER_2_PHYSICALLY_DERIVED',
                    'assumptions': 'No savings quantity is estimated: this rule identifies a relative energy outlier only.',
                })
                rec_id += 1
            # Rule 2: Low efficiency (high SEC)
            if fac_avg_sec > 0 and stats['avg_sec'] > 1.15 * fac_avg_sec:
                recommendations.append({
                    'id': rec_id,
                    'machine_id': m.id,
                    'category': 'Efficiency',
                    'action': 'Inspect spindle speed and torque settings.',
                    'reason': (
                        f"SEC {stats['avg_sec']:.3f} kWh/part exceeds "
                        f"facility average {fac_avg_sec:.3f}."
                    ),
                    'expected_benefit': {},
                    'difficulty': 'Low',
                    'evidence_source': 'Telemetry aggregation',
                    'evidence_summary': (
                        f"{stats['reading_count']} telemetry readings; average SEC exceeds the "
                        "facility average by more than 15%."
                    ),
                    'provenance': 'TIER_2_PHYSICALLY_DERIVED',
                    'assumptions': 'No savings quantity is estimated without a validated intervention baseline.',
                })
                rec_id += 1
            # Rule 3: Frequent anomalies
            if stats['anomaly_count'] > 5:
                recommendations.append({
                    'id': rec_id,
                    'machine_id': m.id,
                    'category': 'Reliability',
                    'action': 'Perform preventive maintenance and root-cause analysis.',
                    'reason': f"{stats['anomaly_count']} anomalies detected for this machine.",
                    'expected_benefit': {},
                    'difficulty': 'High',
                    'evidence_source': 'Anomaly logs',
                    'evidence_summary': f"{stats['anomaly_count']} anomaly events logged for this machine.",
                    'provenance': 'TIER_3_CALIBRATED_CONTEXT',
                    'assumptions': 'Resolving an anomaly does not demonstrate or quantify energy savings.',
                })
                rec_id += 1
        return recommendations
