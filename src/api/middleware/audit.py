"""
감사 추적 미들웨어
"""
import logging
import time
from typing import Callable, Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.requests import Request

from src.services.audit.service import get_audit_service
from src.data.models.audit_models import AuditAction, AuditSeverity

logger = logging.getLogger(__name__)

# 엔드포인트와 감사 액션 매핑
ENDPOINT_ACTION_MAP = {
    "/api/v1/auth/login": AuditAction.LOGIN,
    "/api/v1/auth/logout": AuditAction.LOGOUT,
    "/api/v1/auth/register": AuditAction.USER_CREATE,
    "/api/v1/auth/change-password": AuditAction.PASSWORD_CHANGE,
    "/api/v1/auth/refresh": AuditAction.TOKEN_REFRESH,
    "/api/v1/creator/evaluate": AuditAction.CREATOR_EVALUATE,
    "/api/v1/missions/recommend": AuditAction.MISSION_RECOMMEND,
    "/api/v1/competency/assess": AuditAction.COMPETENCY_ASSESS,
    "/api/v1/recommendations/generate": AuditAction.RECOMMENDATION_GENERATE,
    "/api/v1/search/vector": AuditAction.VECTOR_SEARCH,
    "/api/v1/rag/query": AuditAction.RAG_QUERY,
    "/api/v1/rag/add-documents": AuditAction.DOCUMENT_ADD,
    "/api/v1/analytics/report": AuditAction.ANALYTICS_REPORT,
}


class AuditMiddleware(BaseHTTPMiddleware):
    """감사 추적 미들웨어"""

    def __init__(self, app: Any, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled
        # 감사 대상에서 제외할 경로
        self.exclude_paths = [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 감사 비활성화 또는 제외 경로인 경우 통과
        if not self.enabled or any(
            request.url.path.startswith(path) for path in self.exclude_paths
        ):
            return await call_next(request)

        start_time = time.time()
        audit_service = get_audit_service()

        # 요청 정보 추출
        user_id = getattr(request.state, 'user_id', None)
        username = getattr(request.state, 'username', None)
        role = getattr(request.state, 'role', None)
        if role and hasattr(role, 'value'):
            role = role.value

        request_id = request.headers.get('X-Request-ID')
        ip_address = self._get_client_ip(request)
        user_agent = request.headers.get('User-Agent', '')[:500]

        # 액션 결정
        action = self._determine_action(request)

        response = None
        error_message = None
        success = True

        try:
            response = await call_next(request)

            # 응답 상태 코드로 성공 여부 판단
            if response.status_code >= 400:
                success = False
                if response.status_code >= 500:
                    error_message = f"Server error: {response.status_code}"
                else:
                    error_message = f"Client error: {response.status_code}"

        except Exception as e:
            success = False
            error_message = str(e)
            raise
        finally:
            # 처리 시간 계산
            processing_time = time.time() - start_time

            # 심각도 결정
            if not success:
                if response and response.status_code >= 500:
                    severity = AuditSeverity.ERROR
                else:
                    severity = AuditSeverity.WARNING
            else:
                severity = AuditSeverity.INFO

            # 감사 로그 기록
            try:
                await audit_service.log(
                    action=action,
                    user_id=user_id,
                    username=username,
                    role=role,
                    request_id=request_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    endpoint=str(request.url.path),
                    method=request.method,
                    details={
                        "processing_time_ms": round(processing_time * 1000, 2),
                        "query_params": dict(request.query_params),
                        "status_code": response.status_code if response else None,
                    },
                    success=success,
                    error_message=error_message,
                    severity=severity,
                )
            except Exception as log_error:
                logger.error(f"Failed to write audit log: {log_error}")

        return response

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시/로드밸런서 뒤에 있는 경우)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()

        # X-Real-IP 헤더 확인
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip

        # 직접 연결
        if request.client:
            return request.client.host

        return "unknown"

    def _determine_action(self, request: Request) -> AuditAction:
        """요청에 따른 감사 액션 결정"""
        path = request.url.path

        # 정확한 매칭 확인
        if path in ENDPOINT_ACTION_MAP:
            return ENDPOINT_ACTION_MAP[path]

        # 패턴 매칭
        for endpoint, action in ENDPOINT_ACTION_MAP.items():
            if path.startswith(endpoint):
                return action

        # 기본 액션
        if request.method == "POST":
            if "create" in path or "add" in path:
                return AuditAction.USER_CREATE
        elif request.method in ["PUT", "PATCH"]:
            return AuditAction.USER_UPDATE
        elif request.method == "DELETE":
            return AuditAction.USER_DELETE

        # 매칭되지 않는 경우 기본값
        return AuditAction.RAG_QUERY  # 일반 API 호출
