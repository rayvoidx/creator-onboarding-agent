"""Health check endpoints."""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from config.settings import get_settings
from src.api.schemas.response_schemas import HealthCheckResponse
from src.app.dependencies import get_dependencies

router = APIRouter(tags=["System"])
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """System health check."""
    try:
        deps = get_dependencies()
        settings = get_settings()

        health_status = {
            "api": "healthy",
            "orchestrator": "healthy" if deps.orchestrator else "unhealthy",
            "llm": "healthy" if settings.OPENAI_API_KEY else "not_configured",
        }

        overall_status = (
            "healthy"
            if all(
                status in ["healthy", "disabled"] for status in health_status.values()
            )
            else "unhealthy"
        )

        return HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            components=health_status,
            version="1.0.0",
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="서비스를 이용할 수 없습니다.")
