"""
FastAPI 전역 에러 핸들러

모든 예외를 포착하여 일관된 형식으로 응답합니다.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.exceptions import (
    BaseApplicationException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    RecordNotFoundError,
    ExternalAPIError,
    APITimeoutError,
    APIRateLimitError,
    AgentError,
    DataCollectionError,
    ConfigurationError,
    ErrorSeverity,
    create_error_response,
)

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI):
    """FastAPI 앱에 에러 핸들러 등록"""

    @app.exception_handler(BaseApplicationException)
    async def application_exception_handler(
        request: Request, exc: BaseApplicationException
    ):
        """애플리케이션 예외 핸들러"""
        exc.log()

        # 심각도에 따른 HTTP 상태 코드 결정
        if isinstance(exc, ValidationError):
            status_code = status.HTTP_400_BAD_REQUEST
        elif isinstance(exc, AuthenticationError):
            status_code = status.HTTP_401_UNAUTHORIZED
        elif isinstance(exc, AuthorizationError):
            status_code = status.HTTP_403_FORBIDDEN
        elif isinstance(exc, RecordNotFoundError):
            status_code = status.HTTP_404_NOT_FOUND
        elif isinstance(exc, APIRateLimitError):
            status_code = status.HTTP_429_TOO_MANY_REQUESTS
        elif isinstance(exc, (APITimeoutError, ExternalAPIError)):
            status_code = status.HTTP_502_BAD_GATEWAY
        elif isinstance(exc, DatabaseError):
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        elif exc.severity == ErrorSeverity.CRITICAL:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        return JSONResponse(status_code=status_code, content=create_error_response(exc))

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Pydantic 검증 예외 핸들러"""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {"field": field, "message": error["msg"], "type": error["type"]}
            )

        logger.warning(f"Validation error: {errors}")

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "요청 데이터 검증에 실패했습니다",
                    "category": "validation",
                    "details": {"errors": errors},
                },
            },
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP 예외 핸들러"""
        logger.warning(f"HTTP error {exc.status_code}: {exc.detail}")

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": f"HTTP_{exc.status_code}",
                    "message": str(exc.detail),
                    "category": "http",
                },
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """일반 예외 핸들러 (최종 폴백)"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

        # 프로덕션에서는 상세 정보 숨김
        try:
            from config.settings import get_settings

            debug = get_settings().DEBUG
        except Exception:
            debug = False

        error_message = str(exc) if debug else "내부 서버 오류가 발생했습니다"

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": error_message,
                    "category": "system",
                },
            },
        )

    @app.middleware("http")
    async def error_logging_middleware(request: Request, call_next):
        """에러 로깅 미들웨어"""
        try:
            response = await call_next(request)

            # 4xx, 5xx 응답 로깅
            if response.status_code >= 400:
                logger.info(
                    f"{request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": response.status_code,
                        "client_ip": (
                            request.client.host if request.client else "unknown"
                        ),
                    },
                )

            return response

        except Exception as e:
            logger.error(
                f"Error in middleware: {request.method} {request.url.path} - {e}",
                exc_info=True,
            )
            raise


class CircuitBreakerErrorHandler:
    """서킷 브레이커와 연동된 에러 핸들러"""

    def __init__(self):
        self.failure_counts = {}
        self.last_failure_time = {}
        self.threshold = 5
        self.reset_timeout = 60  # seconds

    def record_failure(self, service_name: str, error: Exception):
        """실패 기록"""
        from datetime import datetime

        if service_name not in self.failure_counts:
            self.failure_counts[service_name] = 0

        self.failure_counts[service_name] += 1
        self.last_failure_time[service_name] = datetime.utcnow()

        logger.warning(
            f"Service {service_name} failure #{self.failure_counts[service_name]}: {error}"
        )

        if self.failure_counts[service_name] >= self.threshold:
            logger.error(f"Service {service_name} circuit breaker triggered!")

    def record_success(self, service_name: str):
        """성공 기록 (카운터 리셋)"""
        self.failure_counts[service_name] = 0

    def is_circuit_open(self, service_name: str) -> bool:
        """서킷 오픈 상태 확인"""
        from datetime import datetime, timedelta

        if service_name not in self.failure_counts:
            return False

        if self.failure_counts[service_name] < self.threshold:
            return False

        # 리셋 타임아웃 확인
        if service_name in self.last_failure_time:
            time_since_failure = (
                datetime.utcnow() - self.last_failure_time[service_name]
            ).total_seconds()

            if time_since_failure > self.reset_timeout:
                # 반-열림 상태로 전환 (다시 시도 허용)
                self.failure_counts[service_name] = self.threshold - 1
                return False

        return True


# 전역 인스턴스
circuit_breaker_handler = CircuitBreakerErrorHandler()
