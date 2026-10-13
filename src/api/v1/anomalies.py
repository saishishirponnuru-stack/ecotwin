"""
Anomalies and Diagnostics API endpoints.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.anomaly_service import AnomalyService
from src.schemas import AnomalyListResponse, AnomalyItem, AnomalyResolveRequest

router = APIRouter(tags=["Anomalies"])


@router.get("/anomalies", response_model=AnomalyListResponse)
def list_anomalies(
    machine_id: Optional[str] = Query(None, description="Filter by machine ID"),
    severity: Optional[str] = Query(None, description="Filter by severity ('watch', 'warning', 'critical')"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List logged statistical energy anomalies and diagnostic reason codes."""
    return AnomalyService.get_anomalies(
        db, machine_id=machine_id, severity=severity, limit=limit, offset=offset
    )


@router.post("/anomalies/{anomaly_id}/resolve", response_model=AnomalyItem)
def resolve_anomaly(
    anomaly_id: int,
    req: AnomalyResolveRequest,
    db: Session = Depends(get_db),
):
    """Mark an anomaly as resolved with operator notes."""
    resolved = AnomalyService.resolve_anomaly(db, anomaly_id=anomaly_id, notes=req.resolution_notes or "Resolved")
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Anomaly event '{anomaly_id}' not found")
    return resolved
