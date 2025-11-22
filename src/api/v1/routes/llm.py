"""LLM management endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from src.app.dependencies import get_dependencies
from config.settings import get_settings

router = APIRouter(prefix="/api/v1/llm", tags=["LLM Management"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_llm_status() -> Dict[str, Any]:
    """Get LLM model status."""
    try:
        deps = get_dependencies()
        if not deps.orchestrator or not deps.orchestrator.llm_manager:
            raise HTTPException(status_code=503, detail="LLM 관리자가 초기화되지 않았습니다.")

        status = await deps.orchestrator.llm_manager.get_model_status()

        return {
            "success": True,
            "models": status,
            "timestamp": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"LLM status check failed: {e}")
        raise HTTPException(status_code=500, detail="LLM 상태 조회 실패")


@router.get("/system/agent-models", tags=["System"])
async def get_agent_model_configs() -> Dict[str, Any]:
    """Get agent model configurations and LLM status."""
    try:
        deps = get_dependencies()
        settings = get_settings()
        agent_configs = settings.AGENT_MODEL_CONFIGS
        llm_status: Dict[str, Any] = {}

        if deps.orchestrator and deps.orchestrator.llm_manager:
            llm_status = await deps.orchestrator.llm_manager.get_model_status()

        return {
            "agent_models": agent_configs,
            "llm_status": llm_status,
            "timestamp": datetime.now().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load agent model configs: {e}")
        raise HTTPException(status_code=500, detail="에이전트 모델 정보를 불러오지 못했습니다.")
