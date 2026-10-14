"""
Anomaly Detection & Diagnostics Service for EcoTwin.
Queries statistical energy anomalies and manages operator resolution statuses.
"""

from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from src.db.models import AnomalyEvent


class AnomalyService:
    @staticmethod
    def get_anomalies(
        db: Session,
        machine_id: Optional[str] = None,
        severity: Optional[str] = None,
        is_resolved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Query logged statistical energy deviations."""
        query = db.query(AnomalyEvent)
        if machine_id:
            query = query.filter(AnomalyEvent.machine_id == machine_id)
        if severity:
            query = query.filter(AnomalyEvent.severity == severity)
        if is_resolved is not None:
            query = query.filter(AnomalyEvent.is_resolved == is_resolved)

        total_count = query.count()
        critical_count = query.filter(AnomalyEvent.severity == "critical").count()
        warning_count = query.filter(AnomalyEvent.severity == "warning").count()
        watch_count = query.filter(AnomalyEvent.severity == "watch").count()

        events = query.order_by(AnomalyEvent.timestamp.desc()).offset(offset).limit(limit).all()

        return {
            "total_count": total_count,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "watch_count": watch_count,
            "anomalies": [e.to_dict() for e in events],
        }

    @staticmethod
    def resolve_anomaly(db: Session, anomaly_id: int, notes: str = "Resolved by operator") -> Optional[Dict[str, Any]]:
        """Acknowledge and resolve an anomaly event."""
        event = db.query(AnomalyEvent).filter(AnomalyEvent.id == anomaly_id).first()
        if not event:
            return None
        event.is_resolved = True
        db.commit()
        db.refresh(event)
        return event.to_dict()
