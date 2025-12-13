"""
인증 서비스 - OAuth2 + JWT 기반 인증/인가 처리
"""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from jose import JWTError, jwt
from passlib.context import CryptContext

from config.settings import get_settings
from src.data.models.user_models import (
    ROLE_PERMISSIONS,
    Permission,
    Token,
    TokenData,
    User,
    UserCreate,
    UserResponse,
    UserRole,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class AuthService:
    """인증 서비스"""

    def __init__(self, redis_url: Optional[str] = None):
        self.secret_key = settings.SECRET_KEY
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis_client: Optional[redis.Redis] = None

        # 인메모리 사용자 저장소 (실제로는 PostgreSQL 사용)
        self._users: Dict[str, User] = {}
        self._users_by_email: Dict[str, str] = {}
        self._users_by_username: Dict[str, str] = {}

        # 블랙리스트 토큰 (Redis 또는 인메모리)
        self._token_blacklist: set = set()

    async def get_redis(self) -> Optional[redis.Redis]:
        """Redis 클라이언트 가져오기"""
        if self._redis_client is None and self.redis_url:
            try:
                self._redis_client = redis.from_url(
                    self.redis_url, encoding="utf-8", decode_responses=True
                )
                await self._redis_client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis_client = None
        return self._redis_client

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """비밀번호 검증"""
        return pwd_context.verify(plain_password, hashed_password)

    def hash_password(self, password: str) -> str:
        """비밀번호 해싱"""
        return pwd_context.hash(password)

    async def create_user(self, user_data: UserCreate) -> UserResponse:
        """사용자 생성"""
        # 이메일 중복 체크
        if user_data.email in self._users_by_email:
            raise ValueError("Email already registered")

        # 사용자명 중복 체크
        if user_data.username in self._users_by_username:
            raise ValueError("Username already taken")

        user_id = str(uuid.uuid4())
        now = datetime.utcnow()

        user = User(
            id=user_id,
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            role=user_data.role,
            hashed_password=self.hash_password(user_data.password),
            created_at=now,
            updated_at=now,
        )

        # 저장
        self._users[user_id] = user
        self._users_by_email[user_data.email] = user_id
        self._users_by_username[user_data.username] = user_id

        logger.info(f"User created: {user_id} ({user_data.username})")

        return self._user_to_response(user)

    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """사용자 인증"""
        user_id = self._users_by_username.get(username)
        if not user_id:
            # 이메일로도 시도
            user_id = self._users_by_email.get(username)

        if not user_id:
            return None

        user = self._users.get(user_id)
        if not user or not user.is_active:
            return None

        if not self.verify_password(password, user.hashed_password):
            return None

        # 마지막 로그인 시간 업데이트
        user.last_login = datetime.utcnow()

        return user

    def create_access_token(
        self, user: User, expires_delta: Optional[timedelta] = None
    ) -> str:
        """액세스 토큰 생성"""
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        permissions = [p.value for p in ROLE_PERMISSIONS.get(user.role, [])]

        payload = {
            "sub": user.id,
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "permissions": permissions,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "access",
        }

        return jwt.encode(payload, self.secret_key, algorithm=ALGORITHM)

    def create_refresh_token(self, user: User) -> str:
        """리프레시 토큰 생성"""
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        payload = {
            "sub": user.id,
            "user_id": user.id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
        }

        return jwt.encode(payload, self.secret_key, algorithm=ALGORITHM)

    async def create_tokens(self, user: User) -> Token:
        """액세스 토큰과 리프레시 토큰 생성"""
        access_token = self.create_access_token(user)
        refresh_token = self.create_refresh_token(user)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def verify_token(self, token: str) -> Optional[TokenData]:
        """토큰 검증 및 디코딩"""
        try:
            # 블랙리스트 확인
            if await self._is_token_blacklisted(token):
                return None

            payload = jwt.decode(token, self.secret_key, algorithms=[ALGORITHM])

            user_id = payload.get("user_id")
            if not user_id:
                return None

            return TokenData(
                user_id=user_id,
                username=payload.get("username", ""),
                email=payload.get("email", ""),
                role=UserRole(payload.get("role", "viewer")),
                permissions=payload.get("permissions", []),
                exp=datetime.fromtimestamp(payload.get("exp", 0)),
                iat=datetime.fromtimestamp(payload.get("iat", 0)),
                jti=payload.get("jti", ""),
            )
        except JWTError as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> Optional[Token]:
        """리프레시 토큰으로 새 액세스 토큰 발급"""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[ALGORITHM])

            if payload.get("type") != "refresh":
                return None

            user_id = payload.get("user_id")
            if not user_id:
                return None

            user = self._users.get(user_id)
            if not user or not user.is_active:
                return None

            # 기존 리프레시 토큰 블랙리스트에 추가
            await self._blacklist_token(refresh_token)

            # 새 토큰 발급
            return await self.create_tokens(user)

        except JWTError as e:
            logger.warning(f"Refresh token verification failed: {e}")
            return None

    async def revoke_token(self, token: str) -> bool:
        """토큰 무효화 (로그아웃)"""
        return await self._blacklist_token(token)

    async def _blacklist_token(self, token: str) -> bool:
        """토큰을 블랙리스트에 추가"""
        try:
            redis_client = await self.get_redis()
            if redis_client:
                # Redis에 저장 (토큰 만료 시간까지만 유지)
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[ALGORITHM],
                    options={"verify_exp": False},
                )
                exp = payload.get("exp", 0)
                ttl = max(0, exp - int(datetime.utcnow().timestamp()))
                if ttl > 0:
                    jti = payload.get("jti", token)
                    await redis_client.setex(f"blacklist:{jti}", ttl, "1")
            else:
                # 인메모리 저장
                self._token_blacklist.add(token)
            return True
        except Exception as e:
            logger.error(f"Failed to blacklist token: {e}")
            return False

    async def _is_token_blacklisted(self, token: str) -> bool:
        """토큰이 블랙리스트에 있는지 확인"""
        try:
            redis_client = await self.get_redis()
            if redis_client:
                payload = jwt.decode(
                    token,
                    self.secret_key,
                    algorithms=[ALGORITHM],
                    options={"verify_exp": False},
                )
                jti = payload.get("jti", token)
                result = await redis_client.get(f"blacklist:{jti}")
                return result is not None
            else:
                return token in self._token_blacklist
        except Exception:
            return False

    def has_permission(self, token_data: TokenData, permission: Permission) -> bool:
        """권한 확인"""
        return permission.value in token_data.permissions

    def has_any_permission(
        self, token_data: TokenData, permissions: List[Permission]
    ) -> bool:
        """주어진 권한 중 하나라도 있는지 확인"""
        return any(p.value in token_data.permissions for p in permissions)

    def has_all_permissions(
        self, token_data: TokenData, permissions: List[Permission]
    ) -> bool:
        """모든 권한을 가지고 있는지 확인"""
        return all(p.value in token_data.permissions for p in permissions)

    async def get_user(self, user_id: str) -> Optional[UserResponse]:
        """사용자 조회"""
        user = self._users.get(user_id)
        if not user:
            return None
        return self._user_to_response(user)

    async def get_user_by_email(self, email: str) -> Optional[UserResponse]:
        """이메일로 사용자 조회"""
        user_id = self._users_by_email.get(email)
        if not user_id:
            return None
        return await self.get_user(user_id)

    async def update_password(
        self, user_id: str, current_password: str, new_password: str
    ) -> bool:
        """비밀번호 변경"""
        user = self._users.get(user_id)
        if not user:
            return False

        if not self.verify_password(current_password, user.hashed_password):
            return False

        user.hashed_password = self.hash_password(new_password)
        user.updated_at = datetime.utcnow()

        logger.info(f"Password changed for user: {user_id}")
        return True

    def _user_to_response(self, user: User) -> UserResponse:
        """User를 UserResponse로 변환"""
        permissions = [p.value for p in ROLE_PERMISSIONS.get(user.role, [])]

        return UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            full_name=user.full_name,
            is_active=user.is_active,
            role=user.role,
            created_at=user.created_at,
            last_login=user.last_login,
            permissions=permissions,
        )


# 싱글톤 인스턴스
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """인증 서비스 인스턴스 반환"""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service
