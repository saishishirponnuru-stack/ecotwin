"""
Executive Overview API endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.overview_service import OverviewService
from src.schemas import ExecutiveOverviewResponse

router = APIRouter(tags=["Overview"])


@router.get("/overview", response_model=ExecutiveOverviewResponse)
def get_overview(db: Session = Depends(get_db)):
    """Executive Command Center energy KPIs, fleet health, and daily trends."""
    return OverviewService.get_executive_overview(db)
