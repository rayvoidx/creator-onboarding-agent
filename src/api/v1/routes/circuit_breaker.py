"""Circuit breaker endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, HTTPException

from src.core.circuit_breaker import get_circuit_breaker_manager

router = APIRouter(prefix="/api/v1/circuit-breaker", tags=["System"])
logger = logging.getLogger(__name__)


@router.get("/status")
async def get_circuit_breaker_status(name: Optional[str] = None) -> Dict[str, Any]:
    """Get circuit breaker status."""
    try:
        manager = get_circuit_breaker_manager()
        status = manager.get_status(name)

        return {
            'success': True,
            'circuit_breakers': status,
            'timestamp': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Circuit breaker status retrieval failed: {e}")
        raise HTTPException(status_code=500, detail="서킷 브레이커 상태 조회 중 오류가 발생했습니다.")


@router.post("/reset/{name}")
async def reset_circuit_breaker(name: str) -> Dict[str, Any]:
    """Force reset circuit breaker."""
    try:
        manager = get_circuit_breaker_manager()
        success = manager.reset(name)

        if not success:
            raise HTTPException(status_code=404, detail=f"서킷 브레이커 '{name}'을 찾을 수 없습니다.")

        return {
            'success': True,
            'message': f"서킷 브레이커 '{name}'이 리셋되었습니다.",
            'timestamp': datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Circuit breaker reset failed: {e}")
        raise HTTPException(status_code=500, detail="서킷 브레이커 리셋 중 오류가 발생했습니다.")
