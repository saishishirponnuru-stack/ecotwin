"""Energy Intelligence API endpoints"""
"""Energy analytics and detailed KPI endpoints for EcoTwin.
Provides machine‑level comparisons, production‑adjusted intensity, cost and emissions estimates.
All calculations reuse existing constants and services to preserve provenance.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.energy_service import EnergyService
from src.schemas import ExecutiveOverviewResponse, MachineListItem

router = APIRouter(tags=["Energy Intelligence"])

@router.get("/energy/overview", response_model=ExecutiveOverviewResponse)
def get_energy_overview(db: Session = Depends(get_db)):
    """Alias to the existing executive overview for backward compatibility."""
    return EnergyService.get_executive_overview(db)

@router.get("/energy/machine-comparison")
def get_machine_comparison(db: Session = Depends(get_db)):
    """Return per‑machine energy intensity and cost/CO₂ metrics.
    Structure is a list of objects with machine id, avg_sec, energy_kwh, cost_inr, co2_tonnes.
    """
    return EnergyService.get_machine_comparison(db)
