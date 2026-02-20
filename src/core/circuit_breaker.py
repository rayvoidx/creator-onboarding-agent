"""
Circuit Breaker 패턴 구현 - 외부 API 장애 격리
"""

import logging
import time
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, Optional

try:
    import pybreaker
except ImportError:
    pybreaker = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    """서킷 브레이커 상태"""

    CLOSED = "closed"  # 정상 상태
    OPEN = "open"  # 장애 상태 (요청 차단)
    HALF_OPEN = "half_open"  # 복구 테스트 중


_CircuitBreakerListenerBase = pybreaker.CircuitBreakerListener if pybreaker else object


class CircuitBreakerListener(_CircuitBreakerListenerBase):  # type: ignore[misc]
    """서킷 브레이커 이벤트 리스너"""

    def __init__(self, name: str):
        self.name = name

    def state_change(self, cb, old_state, new_state):
        """상태 변경 시 로깅"""
        logger.warning(
            f"Circuit breaker '{self.name}' state changed: "
            f"{old_state.name} -> {new_state.name}"
        )

    def failure(self, cb, exc):
        """실패 시 로깅"""
        logger.error(f"Circuit breaker '{self.name}' recorded failure: {exc}")

    def success(self, cb):
        """성공 시 로깅"""
        logger.debug(f"Circuit breaker '{self.name}' recorded success")


class CircuitBreakerManager:
    """서킷 브레이커 관리자"""

    def __init__(self):
        self._breakers: Dict[str, Any] = {}
        self._stats: Dict[str, Dict[str, Any]] = {}

    def get_breaker(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout: int = 30,
        exclude: Optional[tuple] = None,
    ) -> Any:
        """
        서킷 브레이커 가져오기 (없으면 생성)

        Args:
            name: 브레이커 이름 (예: "nile_api", "openai")
            fail_max: 최대 실패 횟수
            reset_timeout: 복구 대기 시간 (초)
            exclude: 제외할 예외 타입

        Returns:
            서킷 브레이커 인스턴스
        """
        if pybreaker is None:
            logger.warning(
                "pybreaker not installed; circuit breaker '%s' disabled", name
            )
            return None

        if name not in self._breakers:
            listener = CircuitBreakerListener(name)

            self._breakers[name] = pybreaker.CircuitBreaker(
                fail_max=fail_max,
                reset_timeout=reset_timeout,
                exclude=exclude or [],
                listeners=[listener],
                name=name,
            )

            self._stats[name] = {
                "created_at": datetime.utcnow().isoformat(),
                "total_calls": 0,
                "successes": 0,
                "failures": 0,
                "state_changes": [],
            }

            logger.info(
                f"Circuit breaker '{name}' created: "
                f"fail_max={fail_max}, reset_timeout={reset_timeout}s"
            )

        return self._breakers[name]

    def get_status(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        서킷 브레이커 상태 조회

        Args:
            name: 브레이커 이름 (None이면 전체)

        Returns:
            상태 정보
        """
        if name:
            if name not in self._breakers:
                return {"error": f"Circuit breaker '{name}' not found"}

            breaker = self._breakers[name]
            return {
                "name": name,
                "state": breaker.current_state,
                "fail_counter": breaker.fail_counter,
                "stats": self._stats.get(name, {}),
            }

        # 전체 상태
        return {
            breaker_name: {
                "state": breaker.current_state,
                "fail_counter": breaker.fail_counter,
                "stats": self._stats.get(breaker_name, {}),
            }
            for breaker_name, breaker in self._breakers.items()
        }

    def reset(self, name: str) -> bool:
        """
        서킷 브레이커 강제 리셋

        Args:
            name: 브레이커 이름

        Returns:
            성공 여부
        """
        if name not in self._breakers:
            return False

        self._breakers[name].close()
        logger.info(f"Circuit breaker '{name}' manually reset")
        return True

    def record_call(self, name: str, success: bool) -> None:
        """호출 통계 기록"""
        if name in self._stats:
            self._stats[name]["total_calls"] += 1
            if success:
                self._stats[name]["successes"] += 1
            else:
                self._stats[name]["failures"] += 1


# 싱글톤 인스턴스
_circuit_breaker_manager: Optional[CircuitBreakerManager] = None


def get_circuit_breaker_manager() -> CircuitBreakerManager:
    """서킷 브레이커 관리자 인스턴스 반환"""
    global _circuit_breaker_manager
    if _circuit_breaker_manager is None:
        _circuit_breaker_manager = CircuitBreakerManager()
    return _circuit_breaker_manager


def circuit_breaker(
    name: str,
    fail_max: int = 5,
    reset_timeout: int = 30,
    fallback: Optional[Callable] = None,
    exclude: Optional[tuple] = None,
):
    """
    서킷 브레이커 데코레이터

    Args:
        name: 브레이커 이름
        fail_max: 최대 실패 횟수
        reset_timeout: 복구 대기 시간 (초)
        fallback: 장애 시 대체 함수
        exclude: 제외할 예외 타입

    Example:
        @circuit_breaker("external_api", fail_max=3, reset_timeout=60)
        async def call_external_api():
            ...
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_breaker(name, fail_max, reset_timeout, exclude)

            # pybreaker not installed – pass through
            if breaker is None:
                return await func(*args, **kwargs)

            try:
                # 서킷이 열려있으면 바로 폴백 실행
                if breaker.current_state == pybreaker.STATE_OPEN:
                    logger.warning(f"Circuit '{name}' is OPEN, using fallback")
                    if fallback:
                        return (
                            await fallback(*args, **kwargs)
                            if callable(fallback)
                            else fallback
                        )
                    raise pybreaker.CircuitBreakerError(
                        f"Circuit breaker '{name}' is open"
                    )

                # 실제 함수 실행
                result = await func(*args, **kwargs)
                breaker.success()  # type: ignore
                manager.record_call(name, True)
                return result

            except pybreaker.CircuitBreakerError:
                manager.record_call(name, False)
                if fallback:
                    return (
                        await fallback(*args, **kwargs)
                        if callable(fallback)
                        else fallback
                    )
                raise

            except Exception as e:
                breaker.failure(e)  # type: ignore
                manager.record_call(name, False)

                # 서킷이 열린 경우 폴백 시도
                if breaker.current_state == pybreaker.STATE_OPEN and fallback:
                    return (
                        await fallback(*args, **kwargs)
                        if callable(fallback)
                        else fallback
                    )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            manager = get_circuit_breaker_manager()
            breaker = manager.get_breaker(name, fail_max, reset_timeout, exclude)

            # pybreaker not installed – pass through
            if breaker is None:
                return func(*args, **kwargs)

            try:
                if breaker.current_state == pybreaker.STATE_OPEN:
                    logger.warning(f"Circuit '{name}' is OPEN, using fallback")
                    if fallback:
                        return (
                            fallback(*args, **kwargs)
                            if callable(fallback)
                            else fallback
                        )
                    raise pybreaker.CircuitBreakerError(
                        f"Circuit breaker '{name}' is open"
                    )

                result = func(*args, **kwargs)
                breaker.success()  # type: ignore
                manager.record_call(name, True)
                return result

            except pybreaker.CircuitBreakerError:
                manager.record_call(name, False)
                if fallback:
                    return fallback(*args, **kwargs) if callable(fallback) else fallback
                raise

            except Exception as e:
                breaker.failure(e)  # type: ignore
                manager.record_call(name, False)

                if breaker.current_state == pybreaker.STATE_OPEN and fallback:
                    return fallback(*args, **kwargs) if callable(fallback) else fallback
                raise

        # 비동기 함수인지 확인
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# 사전 정의된 서킷 브레이커 설정
CIRCUIT_BREAKER_CONFIGS = {
    "nile_api": {"fail_max": 3, "reset_timeout": 60},
    "mohw_api": {"fail_max": 3, "reset_timeout": 60},
    "kicce_api": {"fail_max": 3, "reset_timeout": 60},
    "openai_api": {"fail_max": 5, "reset_timeout": 30},
    "anthropic_api": {"fail_max": 5, "reset_timeout": 30},
    "vector_db": {"fail_max": 3, "reset_timeout": 30},
    "database": {"fail_max": 3, "reset_timeout": 15},
}


def init_circuit_breakers() -> None:
    """모든 사전 정의된 서킷 브레이커 초기화"""
    if pybreaker is None:
        logger.warning("pybreaker not installed; skipping circuit breaker init")
        return

    manager = get_circuit_breaker_manager()

    for name, config in CIRCUIT_BREAKER_CONFIGS.items():
        manager.get_breaker(
            name, fail_max=config["fail_max"], reset_timeout=config["reset_timeout"]
        )

    logger.info(f"Initialized {len(CIRCUIT_BREAKER_CONFIGS)} circuit breakers")
