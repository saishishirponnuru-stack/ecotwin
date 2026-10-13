"""
Health Check API endpoint.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from src.db.database import get_db, DATABASE_URL
from src.db.models import TelemetryReading, Machine
from src.schemas import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
def get_health(db: Session = Depends(get_db)):
    """API health status and persistence verification."""
    db_type = "PostgreSQL" if "postgresql" in DATABASE_URL.lower() else "SQLite"
    total_telemetry = db.query(TelemetryReading).count()
    total_machines = db.query(Machine).count()

    return HealthResponse(
        status="healthy",
        database=db_type,
        total_telemetry_records=total_telemetry,
        total_machines=total_machines,
        data_provenance_model="5-Tier Categorized",
    )
