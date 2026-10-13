"""
API v1 Router aggregation for EcoTwin.
"""

from fastapi import APIRouter

from src.api.v1.health import router as health_router
from src.api.v1.overview import router as overview_router
from src.api.v1.machines import router as machines_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.anomalies import router as anomalies_router
from src.api.v1.whatif import router as whatif_router
from src.api.v1.config import router as config_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(health_router)
api_v1_router.include_router(overview_router)
api_v1_router.include_router(machines_router)
api_v1_router.include_router(telemetry_router)
api_v1_router.include_router(anomalies_router)
api_v1_router.include_router(whatif_router)
api_v1_router.include_router(config_router)

__all__ = ["api_v1_router"]
