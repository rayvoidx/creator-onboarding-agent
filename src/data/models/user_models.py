"""
사용자 인증 및 RBAC 모델
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """사용자 역할"""

    ADMIN = "admin"
    MANAGER = "manager"
    CREATOR = "creator"
    VIEWER = "viewer"


class Permission(str, Enum):
    """시스템 권한"""

    # 크리에이터 관련
    CREATOR_READ = "creator:read"
    CREATOR_WRITE = "creator:write"
    CREATOR_DELETE = "creator:delete"

    # 미션 관련
    MISSION_READ = "mission:read"
    MISSION_WRITE = "mission:write"
    MISSION_DELETE = "mission:delete"
    MISSION_ASSIGN = "mission:assign"

    # 분석 관련
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"

    # 역량 평가 관련
    COMPETENCY_READ = "competency:read"
    COMPETENCY_WRITE = "competency:write"

    # 시스템 관리
    SYSTEM_ADMIN = "system:admin"
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"


# 역할별 권한 매핑
ROLE_PERMISSIONS = {
    UserRole.ADMIN: [p for p in Permission],  # 모든 권한
    UserRole.MANAGER: [
        Permission.CREATOR_READ,
        Permission.CREATOR_WRITE,
        Permission.MISSION_READ,
        Permission.MISSION_WRITE,
        Permission.MISSION_ASSIGN,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.COMPETENCY_READ,
        Permission.COMPETENCY_WRITE,
        Permission.AUDIT_READ,
    ],
    UserRole.CREATOR: [
        Permission.CREATOR_READ,
        Permission.MISSION_READ,
        Permission.ANALYTICS_READ,
        Permission.COMPETENCY_READ,
    ],
    UserRole.VIEWER: [
        Permission.CREATOR_READ,
        Permission.MISSION_READ,
        Permission.ANALYTICS_READ,
    ],
}


class UserBase(BaseModel):
    """사용자 기본 정보"""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None
    is_active: bool = True
    role: UserRole = UserRole.VIEWER


class UserCreate(UserBase):
    """사용자 생성 요청"""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """사용자 업데이트 요청"""

    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None
    password: Optional[str] = None


class User(UserBase):
    """사용자 모델 (DB에서 조회)"""

    id: str
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    """사용자 응답 (비밀번호 제외)"""

    id: str
    email: EmailStr
    username: str
    full_name: Optional[str] = None
    is_active: bool
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: List[str] = []


class Token(BaseModel):
    """JWT 토큰 응답"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """토큰 페이로드 데이터"""

    user_id: str
    username: str
    email: str
    role: UserRole
    permissions: List[str]
    exp: datetime
    iat: datetime
    jti: str  # JWT ID (토큰 고유 식별자)


class RefreshTokenRequest(BaseModel):
    """리프레시 토큰 요청"""

    refresh_token: str


class LoginRequest(BaseModel):
    """로그인 요청"""

    username: str
    password: str


class PasswordChangeRequest(BaseModel):
    """비밀번호 변경 요청"""

    current_password: str
    new_password: str = Field(..., min_length=8)
