"""Explicitly confirmed, narrowly scoped demo-data reset API."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.schemas import DemoDataResetRequest, DemoDataResetResponse
from src.services.demo_data_service import DemoDataResetNotSafe, DemoDataService

router = APIRouter(tags=["Demo Data"])


@router.post("/demo-data/reset", response_model=DemoDataResetResponse)
def reset_demo_data(
    request: DemoDataResetRequest,
    db: Session = Depends(get_db),
):
    """Reopen only the fingerprinted original seeded anomaly events."""
    # The Literal[True] schema rejects missing/false confirmation before here.
    if request.confirm is not True:
        raise HTTPException(status_code=422, detail="Explicit confirmation is required")

    try:
        return DemoDataService.reset_demo_anomalies(db)
    except DemoDataResetNotSafe as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=500,
            detail="The reset transaction failed and was rolled back; no success was recorded.",
        ) from exc
