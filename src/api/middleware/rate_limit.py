"""Rate Limiting 미들웨어"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response
from starlette.requests import Request
from typing import Dict, Callable, Any, Tuple, Optional
from datetime import datetime
import logging

logger: logging.Logger = logging.getLogger(__name__)

try:
    # redis-py 4.2+ provides asyncio support via redis.asyncio
    from redis.asyncio import Redis as AsyncRedis  # type: ignore
except Exception:
    AsyncRedis = None  # type: ignore


class RateLimitMiddleware(BaseHTTPMiddleware):
    """토큰 버킷 알고리즘 기반 요청 제한 미들웨어"""

    def __init__(
        self,
        app: Any,
        enabled: bool = True,
        max_requests: int = 100,
        window_seconds: int = 60,
        redis_url: Optional[str] = None,
        use_redis: bool = False,
        redis_prefix: str = "ratelimit",
    ) -> None:
        super().__init__(app)
        self.enabled = enabled
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.redis_url = redis_url
        self.redis_prefix = redis_prefix
        self._use_redis = bool(use_redis and redis_url and AsyncRedis is not None)
        # IP별 요청 기록 저장 (실제 프로덕션에서는 Redis 사용 권장)
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        # Redis 클라이언트 초기화 (옵션)
        self.redis: Optional[AsyncRedis] = None
        if self._use_redis:
            try:
                self.redis = AsyncRedis.from_url(self.redis_url)  # type: ignore
                logger.info(
                    "RateLimitMiddleware: Using Redis backend for rate limiting"
                )
            except Exception as e:
                logger.warning(
                    f"RateLimitMiddleware: Failed to init Redis backend: {e}. Falling back to in-memory."
                )
                self._use_redis = False

    def _get_client_ip(self, request: Request) -> str:
        """클라이언트 IP 주소 추출"""
        # X-Forwarded-For 헤더 확인 (프록시 뒤에 있을 경우)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _check_rate_limit(self, client_ip: str) -> Tuple[bool, int]:
        """Rate limit 확인 (토큰 버킷 알고리즘)"""
        if self._use_redis and self.redis is not None:
            # 이 메서드는 sync 시그니처지만, Redis 모드는 async 필요 -> dispatch에서 별도 경로 처리
            raise RuntimeError(
                "Redis mode requires async check; call _check_rate_limit_redis instead"
            )
        now = datetime.now()

        # 클라이언트 IP가 처음 요청하는 경우
        if client_ip not in self.request_counts:
            self.request_counts[client_ip] = {"count": 1, "window_start": now}
            return True, self.max_requests - 1

        client_data = self.request_counts[client_ip]
        window_start = client_data["window_start"]
        elapsed = (now - window_start).total_seconds()

        # 시간 창이 지났으면 초기화
        if elapsed > self.window_seconds:
            self.request_counts[client_ip] = {"count": 1, "window_start": now}
            return True, self.max_requests - 1

        # 현재 시간 창 내에서 요청 수 확인
        current_count = client_data["count"]
        if current_count >= self.max_requests:
            remaining_time = int(self.window_seconds - elapsed)
            return False, remaining_time

        # 요청 수 증가
        self.request_counts[client_ip]["count"] += 1
        return True, self.max_requests - current_count - 1

    async def _check_rate_limit_redis(self, client_ip: str) -> Tuple[bool, int]:
        """Rate limit 확인 (Redis 고정 윈도우)"""
        assert self.redis is not None
        try:
            import math

            now = datetime.now()
            epoch = int(now.timestamp())
            window_id = epoch // self.window_seconds
            key = f"{self.redis_prefix}:{client_ip}:{window_id}"
            # 증가 및 만료 설정
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.window_seconds)
            if count > self.max_requests:
                remaining_secs = int(
                    self.window_seconds - (epoch % self.window_seconds)
                )
                return False, remaining_secs
            remaining = max(0, self.max_requests - int(count))
            return True, remaining
        except Exception as e:
            logger.warning(
                f"RateLimitMiddleware: Redis check failed: {e}. Falling back to in-memory for this request."
            )
            return self._check_rate_limit(client_ip)

    def _cleanup_old_entries(self) -> None:
        """오래된 요청 기록 정리 (메모리 관리)"""
        now = datetime.now()
        expired_ips = [
            ip
            for ip, data in self.request_counts.items()
            if (now - data["window_start"]).total_seconds() > self.window_seconds * 2
        ]
        for ip in expired_ips:
            del self.request_counts[ip]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Rate limiting이 비활성화되어 있으면 통과
        if not self.enabled:
            return await call_next(request)

        # 클라이언트 IP 추출
        client_ip = self._get_client_ip(request)

        # Rate limit 확인
        if self._use_redis and self.redis is not None:
            allowed, remaining = await self._check_rate_limit_redis(client_ip)
            used_redis = True
        else:
            allowed, remaining = self._check_rate_limit(client_ip)
            used_redis = False

        if not allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Too many requests",
                    "retry_after": remaining,
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(remaining),
                    "Retry-After": str(remaining),
                },
            )

        # 정상 요청 처리
        response = await call_next(request)

        # Rate limit 헤더 추가
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        if used_redis:
            # 남은 시간 계산 헤더는 2xx일 때 선택적으로 제공하지 않음
            response.headers["X-RateLimit-Backend"] = "redis"
        else:
            response.headers["X-RateLimit-Backend"] = "memory"

        # 주기적으로 오래된 항목 정리 (10% 확률로)
        if len(self.request_counts) > 1000:
            import random

            if random.random() < 0.1:
                self._cleanup_old_entries()

        return response
