"""
What-If Optimization Lab API endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.simulation_service import SimulationService
from src.schemas import (
    WhatIfRequest,
    WhatIfResponse,
    ScenarioSaveRequest,
    ScenarioResponse,
)

router = APIRouter(tags=["What-If Optimization"])


@router.post("/whatif/simulate", response_model=WhatIfResponse)
def simulate_scenario(req: WhatIfRequest, db: Session = Depends(get_db)):
    """
    Simulate operational parameter modifications.
    Enforces coupled machining kinematics and standardized OOD evaluation.
    """
    try:
        return SimulationService.simulate(
            db=db,
            machine_id=req.machine_id,
            spindle_speed_rpm=req.spindle_speed_rpm,
            torque_nm=req.torque_nm,
            tool_replacement=req.tool_replacement or False,
            idle_cutoff_seconds=req.idle_cutoff_seconds,
            shift_reschedule=req.shift_reschedule,
            daily_production=req.daily_production or 800,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/whatif/save", response_model=ScenarioResponse)
def save_scenario(req: ScenarioSaveRequest, db: Session = Depends(get_db)):
    """Save an evaluated What-If scenario to persistent storage."""
    return SimulationService.save_scenario(
        db=db,
        name=req.name,
        machine_id=req.machine_id,
        parameters_in=req.parameters_in,
        result_out=req.result_out,
    )


@router.get("/whatif/scenarios", response_model=List[ScenarioResponse])
def list_scenarios(
    machine_id: Optional[str] = Query(None, description="Filter by machine ID"),
    db: Session = Depends(get_db),
):
    """Retrieve saved What-If optimization scenarios."""
    return SimulationService.list_scenarios(db=db, machine_id=machine_id)
