"""
감사 로그 API 라우터
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Query

from src.services.audit_service import get_audit_service
from src.data.models.audit_models import (
    AuditLogQuery,
    AuditLogResponse,
    AuditAction,
    AuditSeverity,
)
from src.api.middleware.auth import require_permission
from src.data.models.user_models import TokenData, Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["Audit"])


@router.get("/logs", response_model=AuditLogResponse)
async def get_audit_logs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by action"),
    severity: Optional[AuditSeverity] = Query(None, description="Filter by severity"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    limit: int = Query(100, ge=1, le=1000, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
) -> AuditLogResponse:
    """감사 로그 조회"""
    audit_service = get_audit_service()

    query = AuditLogQuery(
        user_id=user_id,
        action=action,
        severity=severity,
        resource_type=resource_type,
        resource_id=resource_id,
        start_date=start_date,
        end_date=end_date,
        success=success,
        limit=limit,
        offset=offset,
    )

    return await audit_service.query(query)


@router.get("/stats")
async def get_audit_stats(
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
) -> Dict[str, Any]:
    """감사 로그 통계 조회"""
    audit_service = get_audit_service()
    stats = await audit_service.get_stats(start_date, end_date)

    return {
        "success": True,
        "stats": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/actions")
async def get_available_actions(
    current_user: TokenData = Depends(require_permission(Permission.AUDIT_READ))
) -> Dict[str, Any]:
    """사용 가능한 감사 액션 목록"""
    return {
        "success": True,
        "actions": [action.value for action in AuditAction],
        "severities": [severity.value for severity in AuditSeverity],
        "timestamp": datetime.utcnow().isoformat()
    }
