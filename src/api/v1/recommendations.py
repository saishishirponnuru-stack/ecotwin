"""
Recommendations API router.
Provides evidence-based operational recommendations generated from
telemetry data and anomaly analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.db.database import get_db
from src.services.recommendation_service import RecommendationService
from src.schemas import RecommendationListResponse

router = APIRouter(tags=["Recommendations"])


@router.get("/recommendations", response_model=RecommendationListResponse)
def list_recommendations(db: Session = Depends(get_db)):
    """Return a list of generated recommendations for the facility."""
    try:
        recs = RecommendationService.generate_all(db)
        return {"recommendations": recs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
