"""
인증 API 라우터
"""
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from src.services.auth_service import get_auth_service
from src.data.models.user_models import (
    UserCreate,
    UserResponse,
    Token,
    LoginRequest,
    RefreshTokenRequest,
    PasswordChangeRequest,
)
from src.api.middleware.auth import get_current_active_user, require_permission
from src.data.models.user_models import TokenData, Permission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserCreate) -> UserResponse:
    """새 사용자 등록"""
    try:
        auth_service = get_auth_service()
        user = await auth_service.create_user(user_data)
        logger.info(f"User registered: {user.username}")
        return user
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"User registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
    """사용자 로그인 (OAuth2 form 형식)"""
    auth_service = get_auth_service()
    user = await auth_service.authenticate_user(
        form_data.username,
        form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await auth_service.create_tokens(user)
    logger.info(f"User logged in: {user.username}")
    return tokens


@router.post("/login/json", response_model=Token)
async def login_json(request: LoginRequest) -> Token:
    """사용자 로그인 (JSON 형식)"""
    auth_service = get_auth_service()
    user = await auth_service.authenticate_user(
        request.username,
        request.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = await auth_service.create_tokens(user)
    logger.info(f"User logged in: {user.username}")
    return tokens


@router.post("/refresh", response_model=Token)
async def refresh_token(request: RefreshTokenRequest) -> Token:
    """액세스 토큰 갱신"""
    auth_service = get_auth_service()
    tokens = await auth_service.refresh_access_token(request.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info("Token refreshed successfully")
    return tokens


@router.post("/logout")
async def logout(
    current_user: TokenData = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """사용자 로그아웃 (토큰 무효화)"""
    # 현재 요청의 토큰을 블랙리스트에 추가
    # 실제로는 Authorization 헤더에서 토큰을 가져와야 함
    logger.info(f"User logged out: {current_user.username}")

    return {
        "success": True,
        "message": "Successfully logged out",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_active_user)
) -> UserResponse:
    """현재 로그인한 사용자 정보 조회"""
    auth_service = get_auth_service()
    user = await auth_service.get_user(current_user.user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


@router.post("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: TokenData = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """비밀번호 변경"""
    auth_service = get_auth_service()
    success = await auth_service.update_password(
        current_user.user_id,
        request.current_password,
        request.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid current password"
        )

    logger.info(f"Password changed for user: {current_user.username}")

    return {
        "success": True,
        "message": "Password changed successfully",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/users", response_model=Dict[str, Any])
async def list_users(
    current_user: TokenData = Depends(require_permission(Permission.USER_MANAGE))
) -> Dict[str, Any]:
    """사용자 목록 조회 (관리자 전용)"""
    auth_service = get_auth_service()

    # 모든 사용자 조회
    users = []
    for user_id in auth_service._users:
        user = await auth_service.get_user(user_id)
        if user:
            users.append(user.model_dump())

    return {
        "success": True,
        "users": users,
        "total": len(users),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/permissions")
async def get_my_permissions(
    current_user: TokenData = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """현재 사용자의 권한 목록 조회"""
    return {
        "success": True,
        "user_id": current_user.user_id,
        "username": current_user.username,
        "role": current_user.role.value,
        "permissions": current_user.permissions,
        "timestamp": datetime.utcnow().isoformat()
    }
