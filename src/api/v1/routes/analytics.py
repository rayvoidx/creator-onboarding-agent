"""Analytics endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.api.schemas.request_schemas import AnalyticsRequest
from src.api.schemas.response_schemas import AnalyticsResponse
from src.app.dependencies import get_dependencies

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])
logger = logging.getLogger(__name__)


@router.post("/report", response_model=AnalyticsResponse)
async def generate_analytics_report(request: AnalyticsRequest) -> AnalyticsResponse:
    """Generate learning analytics report."""
    try:
        deps = get_dependencies()
        if not deps.orchestrator:
            raise HTTPException(
                status_code=503, detail="시스템이 초기화되지 않았습니다."
            )

        result = await deps.orchestrator.run(
            {
                "message": f"{request.report_type} 리포트를 생성해주세요.",
                "user_id": request.user_id,
                "session_id": request.session_id
                or f"analytics_{datetime.now().timestamp()}",
                "context": {
                    "report_type": request.report_type,
                    "date_range": request.date_range,
                    "filters": request.filters,
                    "workflow_type": "analytics",
                    "mcp": request.external_sources or {},
                },
            }
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=500, detail=result.get("error", "리포트 생성 실패")
            )

        return AnalyticsResponse(
            success=True,
            report_id=f"report_{request.user_id}_{datetime.now().timestamp()}",
            report_type=request.report_type,
            user_id=request.user_id,
            report_data=result.get("analytics_results", {}),
            insights=result.get("insights", []),
            recommendations=result.get("recommendations", []),
            timestamp=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analytics report generation failed: {e}")
        raise HTTPException(
            status_code=500, detail="리포트 생성 중 오류가 발생했습니다."
        )
