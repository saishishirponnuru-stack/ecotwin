"""
Machines and Machine Digital Twin API endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.machine_service import MachineService
from src.schemas import MachineListItem, MachineDetailResponse

router = APIRouter(tags=["Machines"])


@router.get("/machines", response_model=List[MachineListItem])
def list_machines(db: Session = Depends(get_db)):
    """List all manufacturing machines in the facility."""
    return MachineService.get_all_machines(db)


@router.get("/machines/{machine_id}", response_model=MachineDetailResponse)
def get_machine_twin(
    machine_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Get real-time digital twin state, operating statistics, and recent telemetry."""
    details = MachineService.get_machine_details(db, machine_id, limit=limit)
    if not details:
        raise HTTPException(status_code=404, detail=f"Machine '{machine_id}' not found")
    return details
