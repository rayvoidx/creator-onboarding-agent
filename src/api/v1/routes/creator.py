"""Creator onboarding endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from src.app.dependencies import get_dependencies
from src.api.schemas.response_schemas import CreatorEvaluationResponse
from src.services.creator_history.service import get_creator_history_service

router = APIRouter(prefix="/api/v1/creator", tags=["Creator"])
logger = logging.getLogger(__name__)


@router.post("/evaluate", response_model=CreatorEvaluationResponse)
async def evaluate_creator(request: Dict[str, Any]) -> CreatorEvaluationResponse:
    """Evaluate creator profiles for onboarding suitability."""
    op_id: Optional[str] = None
    deps = get_dependencies()

    try:
        if deps.performance_monitor:
            op_id = await deps.performance_monitor.start_operation(
                "creator_evaluate",
                metadata={
                    "platform": request.get("platform"),
                    "handle": request.get("handle"),
                },
            )

        if not deps.creator_agent:
            raise HTTPException(status_code=503, detail="Creator agent not initialized")

        # timeout 없이 실행
        result = await deps.creator_agent.execute(request)

        if deps.performance_monitor and op_id:
            deps.performance_monitor.record_creator_result(
                score=result.score,
                decision=result.decision,
            )
            await deps.performance_monitor.end_operation(
                op_id,
                success=True,
                metadata={
                    "score": result.score,
                    "grade": result.grade,
                    "decision": result.decision,
                },
            )

        # Record creator history
        try:
            history_service = get_creator_history_service()
            creator_id = request.get("handle", request.get("creator_id", "unknown"))
            await history_service.record_evaluation(
                creator_id=creator_id,
                platform=result.platform,
                handle=result.handle,
                metrics=request.get("metrics", {}),
                evaluation_result={
                    "grade": result.grade,
                    "score": result.score,
                    "decision": result.decision,
                    "tags": result.tags,
                    "risks": result.risks,
                },
            )
        except Exception as history_error:
            logger.warning(f"Failed to record creator history: {history_error}")

        return CreatorEvaluationResponse(
            success=result.success,
            platform=result.platform,
            handle=result.handle,
            decision=result.decision,
            grade=result.grade,
            score=result.score,
            score_breakdown=result.score_breakdown,
            tags=result.tags,
            risks=result.risks,
            report=result.report,
            raw_profile=result.raw_profile,
            timestamp=datetime.now(),
        )

    except HTTPException:
        if deps.performance_monitor and op_id:
            await deps.performance_monitor.end_operation(
                op_id,
                success=False,
                error_message="HTTPException in creator_evaluate",
            )
        raise
    except Exception as e:
        logger.error(f"Creator evaluation failed: {e}")
        if deps.performance_monitor and op_id:
            await deps.performance_monitor.end_operation(
                op_id,
                success=False,
                error_message=str(e),
            )
        raise HTTPException(
            status_code=500, detail="크리에이터 평가 중 오류가 발생했습니다."
        )
