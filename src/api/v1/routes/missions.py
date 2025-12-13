"""Mission recommendation endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from src.api.schemas.request_schemas import MissionRecommendRequest
from src.api.schemas.response_schemas import (
    MissionRecommendationItem,
    MissionRecommendationResponse,
)
from src.app.dependencies import get_dependencies

router = APIRouter(prefix="/api/v1/missions", tags=["Missions"])
logger = logging.getLogger(__name__)


@router.post("/recommend", response_model=MissionRecommendationResponse)
async def recommend_missions(
    request: MissionRecommendRequest,
) -> MissionRecommendationResponse:
    """Creator-mission matching recommendation API (rule-based v0.1)."""
    op_id: Optional[str] = None
    deps = get_dependencies()

    try:
        if deps.performance_monitor:
            op_id = await deps.performance_monitor.start_operation(
                "mission_recommend",
                metadata={"creator_id": request.creator_id},
            )

        if not deps.orchestrator:
            raise HTTPException(
                status_code=503, detail="시스템이 초기화되지 않았습니다."
            )

        result = await deps.orchestrator.run(
            {
                "message": f"크리에이터 {request.creator_id}에게 적합한 미션을 추천해줘.",
                "user_id": request.creator_id,
                "session_id": request.creator_id,
                "context": {
                    "workflow_type": "mission",
                    "creator_profile": {
                        "creator_id": request.creator_id,
                        **(request.creator_profile or {}),
                    },
                    "onboarding_result": request.onboarding_result or {},
                    "missions": [m.model_dump() for m in request.missions],
                    "filters": request.filters or {},
                    "report_type": "creator_mission_performance",
                    "mcp": request.external_sources or {},
                },
            }
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=500, detail=result.get("error", "미션 추천 실행 실패")
            )

        thread_id = result.get("thread_id", request.creator_id)
        state = await deps.orchestrator.get_session_state(thread_id)

        mission_recs: List[Dict[str, Any]] = []
        if state and state.get("state_exists"):
            mission_recs = result.get("mission_recommendations", []) or []

        items: List[MissionRecommendationItem] = []
        for rec in mission_recs:
            md = rec.get("metadata", {})
            items.append(
                MissionRecommendationItem(
                    mission_id=rec.get("mission_id", ""),
                    mission_name=md.get("mission_name", ""),
                    mission_type=str(md.get("mission_type", "")),
                    reward_type=str(md.get("reward_type", "")),
                    score=float(rec.get("score", 0.0)),
                    reasons=list(rec.get("reasons", [])),
                    metadata=md,
                )
            )

        if deps.performance_monitor and op_id:
            deps.performance_monitor.record_mission_recommendation(
                recommended_count=len(items),
            )
            await deps.performance_monitor.end_operation(
                op_id,
                success=True,
                metadata={
                    "creator_id": request.creator_id,
                    "recommended_count": len(items),
                },
            )

        return MissionRecommendationResponse(
            success=True,
            creator_id=request.creator_id,
            recommendations=items,
            timestamp=datetime.now(),
        )

    except HTTPException:
        if deps.performance_monitor and op_id:
            await deps.performance_monitor.end_operation(
                op_id,
                success=False,
                error_message="HTTPException in mission_recommend",
            )
        raise
    except Exception as e:
        logger.error(f"Mission recommendation API failed: {e}")
        if deps.performance_monitor and op_id:
            await deps.performance_monitor.end_operation(
                op_id,
                success=False,
                error_message=str(e),
            )
        raise HTTPException(
            status_code=500, detail="미션 추천 처리 중 오류가 발생했습니다."
        )
