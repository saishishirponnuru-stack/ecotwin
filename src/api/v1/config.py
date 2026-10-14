"""
Configurable System Settings API endpoint.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.config_service import ConfigService
from src.schemas import ConfigItem, ConfigUpdateRequest

router = APIRouter(tags=["Configuration"])


@router.get("/config", response_model=List[ConfigItem])
def get_config(db: Session = Depends(get_db)):
    """Fetch current tariffs, emission factors, and regulatory parameters."""
    return ConfigService.get_all_settings(db)


@router.put("/config", response_model=List[ConfigItem])
def update_config(req: ConfigUpdateRequest, db: Session = Depends(get_db)):
    """Update configurable tariff or grid emission factors."""
    try:
        return ConfigService.update_settings(db, req.settings)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
