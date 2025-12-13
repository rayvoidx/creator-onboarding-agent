"""
커스텀 예외 및 에러 핸들링 시스템

모든 에이전트와 서비스에서 사용할 수 있는 표준화된 예외 클래스 및 에러 핸들러
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class ErrorSeverity(str, Enum):
    """에러 심각도"""

    LOW = "low"  # 복구 가능, 사용자에게 영향 없음
    MEDIUM = "medium"  # 부분적 기능 저하
    HIGH = "high"  # 주요 기능 실패
    CRITICAL = "critical"  # 시스템 전체 영향


class ErrorCategory(str, Enum):
    """에러 카테고리"""

    VALIDATION = "validation"  # 입력 검증 오류
    AUTHENTICATION = "auth"  # 인증 오류
    AUTHORIZATION = "authz"  # 권한 오류
    DATABASE = "database"  # 데이터베이스 오류
    EXTERNAL_API = "external_api"  # 외부 API 오류
    BUSINESS_LOGIC = "business"  # 비즈니스 로직 오류
    SYSTEM = "system"  # 시스템 오류
    NETWORK = "network"  # 네트워크 오류
    TIMEOUT = "timeout"  # 타임아웃 오류


class BaseApplicationException(Exception):
    """기본 애플리케이션 예외

    모든 커스텀 예외의 기반 클래스
    """

    def __init__(
        self,
        message: str,
        error_code: str = "APP_ERROR",
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.category = category
        self.severity = severity
        self.details = details or {}
        self.original_exception = original_exception
        self.timestamp = datetime.utcnow()
        self.traceback = traceback.format_exc() if original_exception else None

    def to_dict(self) -> Dict[str, Any]:
        """예외를 딕셔너리로 변환"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }

    def log(self):
        """예외를 로그에 기록"""
        log_message = f"[{self.error_code}] {self.message}"

        if self.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, extra=self.to_dict())
        elif self.severity == ErrorSeverity.HIGH:
            logger.error(log_message, extra=self.to_dict())
        elif self.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, extra=self.to_dict())
        else:
            logger.info(log_message, extra=self.to_dict())

        if self.traceback:
            logger.debug(f"Traceback:\n{self.traceback}")


# Backwards compatibility alias
# 일부 레거시 코드에서는 BaseError 이름을 사용하므로, BaseApplicationException을 재노출한다.
BaseError = BaseApplicationException


# Validation Exceptions
class ValidationError(BaseApplicationException):
    """입력 검증 오류"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Any = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if field:
            error_details["field"] = field
        if value is not None:
            error_details["value"] = str(value)[:100]  # 값 truncate

        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            details=error_details,
        )


class MissingFieldError(ValidationError):
    """필수 필드 누락"""

    def __init__(self, field: str):
        super().__init__(message=f"필수 필드가 누락되었습니다: {field}", field=field)
        self.error_code = "MISSING_FIELD"


class InvalidFormatError(ValidationError):
    """잘못된 형식"""

    def __init__(self, field: str, expected_format: str, value: Any = None):
        super().__init__(
            message=f"'{field}' 필드의 형식이 올바르지 않습니다. 예상 형식: {expected_format}",
            field=field,
            value=value,
            details={"expected_format": expected_format},
        )
        self.error_code = "INVALID_FORMAT"


# Authentication/Authorization Exceptions
class AuthenticationError(BaseApplicationException):
    """인증 오류"""

    def __init__(
        self,
        message: str = "인증에 실패했습니다",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code="AUTH_ERROR",
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.MEDIUM,
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """유효하지 않은 토큰"""

    def __init__(self, reason: str = "토큰이 유효하지 않습니다"):
        super().__init__(message=reason, details={"reason": reason})
        self.error_code = "INVALID_TOKEN"


class TokenExpiredError(AuthenticationError):
    """만료된 토큰"""

    def __init__(self):
        super().__init__(message="토큰이 만료되었습니다", details={"reason": "expired"})
        self.error_code = "TOKEN_EXPIRED"


class AuthorizationError(BaseApplicationException):
    """권한 오류"""

    def __init__(
        self,
        message: str = "권한이 없습니다",
        required_permission: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if required_permission:
            error_details["required_permission"] = required_permission

        super().__init__(
            message=message,
            error_code="AUTHZ_ERROR",
            category=ErrorCategory.AUTHORIZATION,
            severity=ErrorSeverity.MEDIUM,
            details=error_details,
        )


# Database Exceptions
class DatabaseError(BaseApplicationException):
    """데이터베이스 오류"""

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if table:
            details["table"] = table

        super().__init__(
            message=message,
            error_code="DB_ERROR",
            category=ErrorCategory.DATABASE,
            severity=ErrorSeverity.HIGH,
            details=details,
            original_exception=original_exception,
        )


class RecordNotFoundError(DatabaseError):
    """레코드를 찾을 수 없음"""

    def __init__(self, entity: str, identifier: Any):
        super().__init__(
            message=f"{entity}을(를) 찾을 수 없습니다: {identifier}", operation="SELECT"
        )
        self.error_code = "NOT_FOUND"
        self.severity = ErrorSeverity.LOW


# Backwards compatibility: 일부 코드에서는 NotFoundError 이름을 사용
NotFoundError = RecordNotFoundError


class DuplicateRecordError(DatabaseError):
    """중복 레코드"""

    def __init__(self, entity: str, field: str, value: Any):
        super().__init__(
            message=f"{entity}의 {field} 값이 이미 존재합니다: {value}",
            operation="INSERT",
        )
        self.error_code = "DUPLICATE_RECORD"
        self.severity = ErrorSeverity.LOW


# External API Exceptions
class ExternalAPIError(BaseApplicationException):
    """외부 API 오류"""

    def __init__(
        self,
        message: str,
        api_name: str,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        details = {"api_name": api_name}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body[:500]

        super().__init__(
            message=message,
            error_code="EXTERNAL_API_ERROR",
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            original_exception=original_exception,
        )


class APITimeoutError(ExternalAPIError):
    """API 타임아웃"""

    def __init__(self, api_name: str, timeout_seconds: int):
        super().__init__(
            message=f"{api_name} API 요청이 {timeout_seconds}초 후 타임아웃되었습니다",
            api_name=api_name,
        )
        self.error_code = "API_TIMEOUT"
        self.category = ErrorCategory.TIMEOUT
        self.details["timeout_seconds"] = timeout_seconds


class APIRateLimitError(ExternalAPIError):
    """API 속도 제한"""

    def __init__(self, api_name: str, retry_after: Optional[int] = None):
        super().__init__(
            message=f"{api_name} API 요청 속도 제한에 도달했습니다",
            api_name=api_name,
            status_code=429,
        )
        self.error_code = "API_RATE_LIMIT"
        if retry_after:
            self.details["retry_after_seconds"] = retry_after


# Agent Exceptions
class AgentError(BaseApplicationException):
    """에이전트 오류"""

    def __init__(
        self,
        message: str,
        agent_name: str,
        state: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        details = {"agent_name": agent_name}
        if state:
            # 민감 정보 제외
            safe_state = {k: v for k, v in state.items() if not k.startswith("_")}
            details["state"] = safe_state

        super().__init__(
            message=message,
            error_code="AGENT_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            original_exception=original_exception,
        )


class AgentExecutionError(AgentError):
    """에이전트 실행 오류"""

    def __init__(
        self, agent_name: str, step: str, original_exception: Optional[Exception] = None
    ):
        super().__init__(
            message=f"{agent_name}의 '{step}' 단계에서 실행 오류가 발생했습니다",
            agent_name=agent_name,
            original_exception=original_exception,
        )
        self.error_code = "AGENT_EXECUTION_ERROR"
        self.details["step"] = step


class AgentStateError(AgentError):
    """에이전트 상태 오류"""

    def __init__(self, agent_name: str, reason: str):
        super().__init__(
            message=f"{agent_name}의 상태가 올바르지 않습니다: {reason}",
            agent_name=agent_name,
        )
        self.error_code = "AGENT_STATE_ERROR"


# Data Collection Exceptions
class DataCollectionError(BaseApplicationException):
    """데이터 수집 오류"""

    def __init__(
        self,
        message: str,
        source: str,
        items_collected: int = 0,
        items_failed: int = 0,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code="DATA_COLLECTION_ERROR",
            category=ErrorCategory.EXTERNAL_API,
            severity=ErrorSeverity.MEDIUM,
            details={
                "source": source,
                "items_collected": items_collected,
                "items_failed": items_failed,
            },
            original_exception=original_exception,
        )


class DataProcessingError(BaseApplicationException):
    """데이터 처리 오류"""

    def __init__(
        self,
        message: str,
        processor: str,
        item_id: Optional[str] = None,
        original_exception: Optional[Exception] = None,
    ):
        details = {"processor": processor}
        if item_id:
            details["item_id"] = item_id

        super().__init__(
            message=message,
            error_code="DATA_PROCESSING_ERROR",
            category=ErrorCategory.BUSINESS_LOGIC,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            original_exception=original_exception,
        )


# Configuration Exceptions
class ConfigurationError(BaseApplicationException):
    """설정 오류"""

    def __init__(self, message: str, config_key: Optional[str] = None):
        details = {}
        if config_key:
            details["config_key"] = config_key

        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            details=details,
        )


# Error Handler Helper Functions
def handle_exception(
    exception: Exception, context: Optional[Dict[str, Any]] = None, reraise: bool = True
) -> BaseApplicationException:
    """예외를 표준화된 형식으로 처리

    Args:
        exception: 원본 예외
        context: 추가 컨텍스트 정보
        reraise: 처리 후 재발생 여부

    Returns:
        표준화된 예외
    """
    if isinstance(exception, BaseApplicationException):
        app_exception = exception
    else:
        app_exception = BaseApplicationException(
            message=str(exception), original_exception=exception, details=context or {}
        )

    app_exception.log()

    if reraise:
        raise app_exception

    return app_exception


def create_error_response(exception: BaseApplicationException) -> Dict[str, Any]:
    """API 응답용 에러 딕셔너리 생성"""
    response = {
        "success": False,
        "error": {
            "code": exception.error_code,
            "message": exception.message,
            "category": exception.category.value,
        },
    }

    # 개발 환경에서만 상세 정보 포함
    try:
        from config.settings import get_settings

        if get_settings().DEBUG:
            response["error"]["details"] = exception.details
            if exception.traceback:
                response["error"]["traceback"] = exception.traceback
    except Exception:
        pass

    return response


class ErrorAggregator:
    """다중 에러 집계기

    여러 작업에서 발생한 에러를 수집하고 요약합니다.
    """

    def __init__(self):
        self.errors: list[BaseApplicationException] = []

    def add(self, error: BaseApplicationException):
        """에러 추가"""
        self.errors.append(error)

    def add_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ):
        """일반 예외를 변환하여 추가"""
        if isinstance(exception, BaseApplicationException):
            self.errors.append(exception)
        else:
            self.errors.append(
                BaseApplicationException(
                    message=str(exception),
                    original_exception=exception,
                    details=context or {},
                )
            )

    def has_errors(self) -> bool:
        """에러 존재 여부"""
        return len(self.errors) > 0

    def has_critical_errors(self) -> bool:
        """중요 에러 존재 여부"""
        return any(
            e.severity in (ErrorSeverity.HIGH, ErrorSeverity.CRITICAL)
            for e in self.errors
        )

    def get_summary(self) -> Dict[str, Any]:
        """에러 요약"""
        if not self.errors:
            return {"total": 0, "errors": []}

        by_category = {}
        by_severity = {}

        for error in self.errors:
            cat = error.category.value
            sev = error.severity.value

            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total": len(self.errors),
            "by_category": by_category,
            "by_severity": by_severity,
            "errors": [e.to_dict() for e in self.errors[:10]],  # 최대 10개
        }

    def log_all(self):
        """모든 에러 로깅"""
        for error in self.errors:
            error.log()
