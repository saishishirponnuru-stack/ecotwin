"""
Telemetry API endpoint.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.db.models import TelemetryReading
from src.schemas import TelemetryListResponse

router = APIRouter(tags=["Telemetry"])


@router.get("/telemetry", response_model=TelemetryListResponse)
def get_telemetry(
    machine_id: Optional[str] = Query(None, description="Filter by machine ID"),
    limit: int = Query(50, ge=1, le=500),
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
):
    """Query telemetry records with provenance tiers."""
    query = db.query(TelemetryReading)
    if machine_id:
        query = query.filter(TelemetryReading.machine_id == machine_id)

    total_count = query.count()
    offset = (page - 1) * limit
    records = query.order_by(TelemetryReading.timestamp.desc()).offset(offset).limit(limit).all()

    return TelemetryListResponse(
        total_count=total_count,
        page=page,
        limit=limit,
        records=[r.to_dict() for r in records],
    )
