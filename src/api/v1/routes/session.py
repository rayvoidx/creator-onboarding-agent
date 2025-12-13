"""Session management endpoints."""

import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException

from src.app.dependencies import get_dependencies

router = APIRouter(prefix="/api/v1/session", tags=["Session"])
logger = logging.getLogger(__name__)


@router.get("/{session_id}")
async def get_session_state(session_id: str) -> Dict[str, Any]:
    """Get session state."""
    try:
        deps = get_dependencies()

        if not deps.orchestrator:
            raise HTTPException(
                status_code=500, detail="오케스트레이터가 초기화되지 않았습니다."
            )

        session_state = await deps.orchestrator.get_session_state(session_id)

        if not session_state:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

        return {
            "success": True,
            "session_state": session_state,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session state retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail="세션 상태 조회 중 오류가 발생했습니다."
        )


@router.post("/{session_id}/resume")
async def resume_session(session_id: str, message: str) -> Dict[str, Any]:
    """Resume session and continue execution."""
    try:
        deps = get_dependencies()

        if not deps.orchestrator:
            raise HTTPException(
                status_code=500, detail="오케스트레이터가 초기화되지 않았습니다."
            )

        result = await deps.orchestrator.resume_session(session_id, message)

        if not result.get("success", False):
            raise HTTPException(
                status_code=400, detail=result.get("error", "세션 복원에 실패했습니다.")
            )

        return {
            "success": True,
            "result": result,
            "timestamp": datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Session resume failed: {e}")
        raise HTTPException(status_code=500, detail="세션 복원 중 오류가 발생했습니다.")


@router.delete("/{session_id}")
async def clear_session(session_id: str) -> Dict[str, Any]:
    """Delete session state."""
    try:
        deps = get_dependencies()

        if not deps.orchestrator:
            raise HTTPException(
                status_code=500, detail="오케스트레이터가 초기화되지 않았습니다."
            )

        success = await deps.orchestrator.clear_session(session_id)

        return {
            "success": success,
            "message": (
                "세션이 삭제되었습니다." if success else "세션 삭제에 실패했습니다."
            ),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Session clear failed: {e}")
        raise HTTPException(status_code=500, detail="세션 삭제 중 오류가 발생했습니다.")
