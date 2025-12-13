"""
감사 추적 모델
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """감사 이벤트 액션 타입"""

    # 인증 관련
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"

    # 사용자 관련
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"

    # 크리에이터 관련
    CREATOR_EVALUATE = "creator_evaluate"
    CREATOR_UPDATE = "creator_update"

    # 미션 관련
    MISSION_CREATE = "mission_create"
    MISSION_UPDATE = "mission_update"
    MISSION_DELETE = "mission_delete"
    MISSION_ASSIGN = "mission_assign"
    MISSION_RECOMMEND = "mission_recommend"

    # 역량 평가 관련
    COMPETENCY_ASSESS = "competency_assess"
    RECOMMENDATION_GENERATE = "recommendation_generate"

    # RAG/검색 관련
    RAG_QUERY = "rag_query"
    DOCUMENT_ADD = "document_add"
    VECTOR_SEARCH = "vector_search"

    # 분석 관련
    ANALYTICS_REPORT = "analytics_report"

    # 시스템 관련
    SYSTEM_CONFIG_CHANGE = "system_config_change"
    DATA_EXPORT = "data_export"
    DATA_IMPORT = "data_import"

    # 에러/예외
    ERROR = "error"
    SECURITY_ALERT = "security_alert"


class AuditSeverity(str, Enum):
    """감사 이벤트 심각도"""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditLog(BaseModel):
    """감사 로그 모델"""

    id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # 사용자 정보
    user_id: Optional[str] = None
    username: Optional[str] = None
    role: Optional[str] = None

    # 이벤트 정보
    action: AuditAction
    severity: AuditSeverity = AuditSeverity.INFO
    resource_type: Optional[str] = None  # creator, mission, user, etc.
    resource_id: Optional[str] = None

    # 요청 정보
    request_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None

    # 상세 정보
    details: Dict[str, Any] = Field(default_factory=dict)
    old_value: Optional[Dict[str, Any]] = None  # 변경 전 값
    new_value: Optional[Dict[str, Any]] = None  # 변경 후 값

    # 결과
    success: bool = True
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogCreate(BaseModel):
    """감사 로그 생성 요청"""

    action: AuditAction
    severity: AuditSeverity = AuditSeverity.INFO
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditLogQuery(BaseModel):
    """감사 로그 조회 필터"""

    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    severity: Optional[AuditSeverity] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    success: Optional[bool] = None
    limit: int = 100
    offset: int = 0


class AuditLogResponse(BaseModel):
    """감사 로그 응답"""

    logs: list[AuditLog]
    total: int
    limit: int
    offset: int
