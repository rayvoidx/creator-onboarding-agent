"""Search endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from src.app.dependencies import get_dependencies
from src.api.schemas.request_schemas import SearchRequest
from src.api.schemas.response_schemas import SearchResponse

router = APIRouter(prefix="/api/v1/search", tags=["Search"])
logger = logging.getLogger(__name__)


@router.post("/vector", response_model=SearchResponse)
async def vector_search(request: SearchRequest) -> SearchResponse:
    """Vector-based knowledge search."""
    try:
        deps = get_dependencies()
        if not deps.orchestrator:
            raise HTTPException(
                status_code=503, detail="시스템이 초기화되지 않았습니다."
            )

        result = await deps.orchestrator.run(
            {
                "message": f"다음 내용을 검색해주세요: {request.query}",
                "user_id": request.user_id,
                "session_id": request.session_id
                or f"search_{datetime.now().timestamp()}",
                "context": {
                    "search_query": request.query,
                    "filters": request.filters,
                    "limit": request.limit,
                    "workflow_type": "search",
                },
            }
        )

        if not result.get("success", False):
            raise HTTPException(
                status_code=500, detail=result.get("error", "검색 실행 실패")
            )

        return SearchResponse(
            success=True,
            query=request.query,
            results=result.get("search_results", []),
            total_count=len(result.get("search_results", [])),
            search_time=result.get("performance_metrics", {}).get(
                "total_execution_time", 0
            ),
            timestamp=datetime.now(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector search failed: {e}")
        raise HTTPException(status_code=500, detail="검색 처리 중 오류가 발생했습니다.")
