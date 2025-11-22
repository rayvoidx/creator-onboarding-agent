"""Recommendation endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.app.dependencies import get_dependencies
from src.api.schemas.request_schemas import RecommendationRequest
from src.api.schemas.response_schemas import RecommendationResponse

router = APIRouter(prefix="/api/v1/recommendations", tags=["Recommendations"])
logger = logging.getLogger(__name__)


@router.post("/generate", response_model=RecommendationResponse)
async def generate_recommendations(
    request: RecommendationRequest
) -> RecommendationResponse:
    """Generate personalized learning material recommendations."""
    try:
        deps = get_dependencies()
        if not deps.orchestrator:
            raise HTTPException(status_code=503, detail="시스템이 초기화되지 않았습니다.")

        result = await deps.orchestrator.run({
            "message": f"맞춤형 추천을 생성해주세요. 사용자ID: {request.user_id}",
            "user_id": request.user_id,
            "session_id": request.session_id,
            "context": {
                "user_profile": request.user_profile,
                "learning_preferences": request.learning_preferences,
                "competency_data": request.competency_data,
                "workflow_type": "recommendation"
            }
        })

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "추천 생성 실패"))

        return RecommendationResponse(
            success=True,
            user_id=request.user_id,
            recommendations=result.get("recommendations", []),
            confidence_score=result.get("confidence_score", 0.0),
            reasoning=result.get("reasoning", ""),
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Recommendation generation failed: {e}")
        raise HTTPException(status_code=500, detail="추천 생성 중 오류가 발생했습니다.")
