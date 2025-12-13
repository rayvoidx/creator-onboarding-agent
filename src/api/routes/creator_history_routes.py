"""
크리에이터 이력 API 라우터
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.middleware.auth import require_permission
from src.data.models.creator_history_models import (
    CreatorHistoryQuery,
    CreatorHistoryResponse,
    CreatorTrend,
)
from src.data.models.user_models import Permission, TokenData
from src.services.creator_history.service import get_creator_history_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/creators", tags=["Creator History"])


@router.get("/{creator_id}/history", response_model=CreatorHistoryResponse)
async def get_creator_history(
    creator_id: str,
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: TokenData = Depends(require_permission(Permission.CREATOR_READ)),
) -> CreatorHistoryResponse:
    """크리에이터 이력 조회"""
    history_service = get_creator_history_service()

    query = CreatorHistoryQuery(
        creator_id=creator_id,
        start_date=start_date,
        end_date=end_date,
        change_type=change_type,
        limit=limit,
        offset=offset,
    )

    return await history_service.get_history(query)


@router.get("/{creator_id}/trend")
async def get_creator_trend(
    creator_id: str,
    period_days: int = Query(30, ge=1, le=365, description="Analysis period in days"),
    current_user: TokenData = Depends(require_permission(Permission.CREATOR_READ)),
) -> Dict[str, Any]:
    """크리에이터 트렌드 분석"""
    history_service = get_creator_history_service()

    trend = await history_service.get_trend(creator_id, period_days)

    if not trend:
        return {
            "success": False,
            "message": "Not enough data for trend analysis",
            "creator_id": creator_id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    return {
        "success": True,
        "trend": trend.model_dump(),
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/{creator_id}/mission-complete")
async def record_mission_completion(
    creator_id: str,
    mission_id: str,
    mission_name: str,
    performance_metrics: Optional[Dict[str, Any]] = None,
    current_user: TokenData = Depends(require_permission(Permission.MISSION_WRITE)),
) -> Dict[str, Any]:
    """미션 완료 기록"""
    history_service = get_creator_history_service()

    entry = await history_service.record_mission_completion(
        creator_id=creator_id,
        mission_id=mission_id,
        mission_name=mission_name,
        performance_metrics=performance_metrics,
    )

    return {
        "success": True,
        "entry_id": entry.id,
        "message": f"Mission completion recorded: {mission_name}",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/{creator_id}/snapshots")
async def get_creator_snapshots(
    creator_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of snapshots"),
    current_user: TokenData = Depends(require_permission(Permission.CREATOR_READ)),
) -> Dict[str, Any]:
    """크리에이터 스냅샷 목록 조회"""
    history_service = get_creator_history_service()

    query = CreatorHistoryQuery(
        creator_id=creator_id,
        limit=limit,
    )

    result = await history_service.get_history(query)

    return {
        "success": True,
        "creator_id": creator_id,
        "snapshots": [s.model_dump() for s in result.snapshots],
        "total": len(result.snapshots),
        "timestamp": datetime.utcnow().isoformat(),
    }
