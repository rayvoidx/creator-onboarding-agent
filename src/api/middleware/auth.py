"""인증 및 권한 관련 유틸리티.

FastAPI 의존성(Depends)에서 사용할 수 있는 헬퍼와
Starlette BaseHTTPMiddleware 기반 JWT 인증 미들웨어를 제공합니다.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, List

import jwt  # type: ignore
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from starlette.responses import JSONResponse, Response

from config.settings import get_settings
from src.data.models.user_models import Permission, TokenData


logger: logging.Logger = logging.getLogger(__name__)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def _decode_token(token: str) -> TokenData:
    """JWT 토큰을 디코드하여 TokenData로 반환."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return TokenData(**payload)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    """현재 활성 사용자(토큰 기반)를 반환하는 FastAPI 의존성."""
    user = _decode_token(token)
    # 추가적으로 is_active 등을 체크하려면 여기서 확장
    return user


def require_permission(required: Permission) -> Callable[[TokenData], TokenData]:
    """특정 Permission이 필요한 엔드포인트에 사용하는 의존성 팩토리."""

    async def dependency(
        user: TokenData = Depends(get_current_active_user),
    ) -> TokenData:
        if required.value not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{required.value}' required",
            )
        return user

    return dependency


class AuthMiddleware(BaseHTTPMiddleware):
    """JWT 기반 인증 미들웨어 (주요 API 보호용).

    - FastAPI 라우트에서는 `get_current_active_user`/`require_permission` 을 쓰고,
    - 미들웨어는 단순히 최소한의 JWT 유효성만 확인해도 충분합니다.
    """

    def __init__(self, app: Any, secret_key: str, enabled: bool = True) -> None:
        super().__init__(app)
        self.secret_key = secret_key
        self.enabled = enabled
        # 인증이 필요 없는 경로들
        self.exempt_paths: List[str] = [
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/v1/creator",
            "/api/v1/missions",
            "/api/v1/analytics",
            "/api/v1/search",
            "/api/v1/competency",
            "/api/v1/recommendations",
            "/metrics",
            "/api/v1/auth/login",
            "/api/v1/auth/login/json",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
        ]

    async def dispatch(
        self, request: StarletteRequest, call_next: Callable
    ) -> Response:
        # 인증이 비활성화되어 있거나 제외 경로인 경우 통과
        if not self.enabled or any(
            request.url.path.startswith(path) for path in self.exempt_paths
        ):
            return await call_next(request)

        # Authorization 헤더 확인
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Missing authorization header"},
            )

        # Bearer 토큰 추출
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != "bearer":
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "success": False,
                        "error": "Invalid authentication scheme",
                    },
                )
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "success": False,
                    "error": "Invalid authorization header format",
                },
            )

        # JWT 토큰 검증 (payload는 필요 시 state에 붙일 수 있음)
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            request.state.user_id = payload.get("user_id")
            request.state.session_id = payload.get("session_id")
        except jwt.ExpiredSignatureError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Token has expired"},
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"success": False, "error": "Invalid token"},
            )

        return await call_next(request)
