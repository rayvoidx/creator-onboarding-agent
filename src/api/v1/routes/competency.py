"""Competency assessment endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.app.dependencies import get_dependencies
from src.api.schemas.request_schemas import CompetencyAssessmentRequest
from src.api.schemas.response_schemas import CompetencyAssessmentResponse
from typing import Dict, Any

router = APIRouter(prefix="/api/v1/competency", tags=["Competency"])
logger = logging.getLogger(__name__)


async def save_assessment_result(user_id: str, result: Dict[str, Any]) -> None:
    """Save assessment result (background task)."""
    try:
        logger.info(f"Saving assessment result for user {user_id}")
    except Exception as e:
        logger.error(f"Failed to save assessment result: {e}")


@router.post("/assess", response_model=CompetencyAssessmentResponse)
async def assess_competency(
    request: CompetencyAssessmentRequest,
    background_tasks: BackgroundTasks
) -> CompetencyAssessmentResponse:
    """Perform competency assessment."""
    try:
        deps = get_dependencies()
        if not deps.orchestrator:
            raise HTTPException(status_code=503, detail="시스템이 초기화되지 않았습니다.")

        result = await deps.orchestrator.run({
            "message": f"역량진단을 수행해주세요. 사용자ID: {request.user_id}",
            "user_id": request.user_id,
            "session_id": request.session_id,
            "context": {
                "assessment_data": request.assessment_data,
                "workflow_type": "competency",
                "require_detailed_analysis": True
            }
        })

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "역량진단 실행 실패"))

        background_tasks.add_task(save_assessment_result, request.user_id, result)

        return CompetencyAssessmentResponse(
            success=True,
            assessment_id=f"assess_{request.user_id}_{datetime.now().timestamp()}",
            user_id=request.user_id,
            analysis_result=result.get("response", {}),
            recommendations=result.get("recommendations", []),
            performance_metrics=result.get("performance_metrics", {}),
            timestamp=datetime.now()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Competency assessment failed: {e}")
        raise HTTPException(status_code=500, detail="역량진단 처리 중 오류가 발생했습니다.")
