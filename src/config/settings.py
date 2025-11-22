"""
애플리케이션 설정 모듈
"""
import os
import secrets
from typing import List, Dict, Any
from pydantic import Field  # type: ignore[import-not-found]
from pydantic_settings import BaseSettings, SettingsConfigDict  # type: ignore[import-not-found]


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")  # Gemini API
    VOYAGE_API_KEY: str = os.getenv("VOYAGE_API_KEY", "")  # Voyage AI 임베딩용
    # Web search (optional)
    BRAVE_API_KEY: str = os.getenv("BRAVE_API_KEY", "")
    SERPAPI_API_KEY: str = os.getenv("SERPAPI_API_KEY", "")

    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/ai_learning_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Vector DB - Pinecone only
    VECTOR_DB_PROVIDER: str = "pinecone"
    PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
    PINECONE_ENVIRONMENT: str = os.getenv("PINECONE_ENVIRONMENT", "us-east-1-aws")
    PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "creator-onboarding")
    PINECONE_NAMESPACE: str = os.getenv("PINECONE_NAMESPACE", "default")

    # Application
    ENV: str = os.getenv("ENV", "development").lower()
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    LOG_LEVEL: str = "INFO"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Cloud/Infra (Naver Cloud 지원)
    CLOUD_PROVIDER: str = os.getenv("CLOUD_PROVIDER", "ncp")
    NCLOUD_ACCESS_KEY_ID: str = os.getenv("NCLOUD_ACCESS_KEY_ID", "")
    NCLOUD_SECRET_KEY: str = os.getenv("NCLOUD_SECRET_KEY", "")
    NCLOUD_REGION: str = os.getenv("NCLOUD_REGION", "kr")
    NCLOUD_ZONE: str = os.getenv("NCLOUD_ZONE", "kr-1")

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ENABLE_AUTH: bool = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    ENABLE_RATE_LIMITING: bool = True
    RATE_LIMIT_USE_REDIS: bool = os.getenv("RATE_LIMIT_USE_REDIS", "false").lower() == "true"

    # CORS
    # 환경 변수로 설정 시: ALLOWED_ORIGINS='["http://localhost:3000","http://localhost:8000"]'
    # 또는 콤마 구분: ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:8000")

    @property
    def allowed_origins_list(self) -> List[str]:
        """ALLOWED_ORIGINS를 리스트로 반환"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            # 콤마로 구분된 문자열을 리스트로 변환
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]
        return self.ALLOWED_ORIGINS

    # LLM Models - Provider-specific model names
    # Anthropic Models
    ANTHROPIC_MODEL_NAME: str = os.getenv("ANTHROPIC_MODEL_NAME", "claude-sonnet-4-20250514")
    # Gemini Models
    GEMINI_MODEL_NAME: str = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash")
    # OpenAI Models
    OPENAI_MODEL_NAME: str = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

    # LLM - Default configurations
    # 일반 대화 기본 모델(일반용)
    DEFAULT_LLM_MODEL: str = os.getenv("DEFAULT_LLM_MODEL", "claude-sonnet-4-20250514")
    # 폴백/가속 모델(저부하/빠른 응답)
    FAST_LLM_MODEL: str = os.getenv("FAST_LLM_MODEL", "gemini-2.0-flash")
    # 심화/대용량 컨텍스트 모델(고난도/심화 질문)
    DEEP_LLM_MODEL: str = os.getenv("DEEP_LLM_MODEL", "gpt-4o")
    # 역사적 호환을 위해 유지하되 내부적으로 FAST로 매핑
    FALLBACK_LLM_MODEL: str = os.getenv("FALLBACK_LLM_MODEL", "gemini-2.0-flash")

    # Embedding Models
    EMBEDDING_MODEL_NAME: str = os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-3-large")
    GEMINI_EMBEDDING_MODEL_NAME: str = os.getenv("GEMINI_EMBEDDING_MODEL_NAME", "text-embedding-004")
    VOYAGE_EMBEDDING_MODEL_NAME: str = os.getenv("VOYAGE_EMBEDDING_MODEL_NAME", "voyage-3")

    # Default embedding provider (openai, gemini, voyage)
    DEFAULT_EMBEDDING_PROVIDER: str = os.getenv("DEFAULT_EMBEDDING_PROVIDER", "voyage")

    # Prompt config
    PROMPT_CONFIG_PATH: str = os.getenv("PROMPT_CONFIG_PATH", "./prompts.yaml")
    PROMPT_DEFAULT_VERSION: str = os.getenv("PROMPT_DEFAULT_VERSION", "v1")
    PROMPT_AB_TEST_ENABLED: bool = os.getenv("PROMPT_AB_TEST_ENABLED", "false").lower() == "true"

    # (Optional) CLOVA Studio 키 - 현재 LLM은 OpenAI/Anthropic 사용, 서버만 NCP에 배포
    CLOVASTUDIO_API_KEY: str = os.getenv("CLOVASTUDIO_API_KEY", "")

    # OCR/Tesseract
    TESSERACT_CMD: str = os.getenv("TESSERACT_CMD", "")
    TESSDATA_PREFIX: str = os.getenv("TESSDATA_PREFIX", "")
    OCR_CLEAN_FILTERS: str = os.getenv("OCR_CLEAN_FILTERS", "\t,\n,\r")

    # Reranker/Query expansion
    RERANKER_THRESHOLD: float = float(os.getenv("RERANKER_THRESHOLD", "0.0"))
    QUERY_EXPANSION_ENABLED: bool = os.getenv("QUERY_EXPANSION_ENABLED", "false").lower() == "true"

    # Deep Agents (optional knobs)
    DEEPAGENT_MAX_STEPS: int = int(os.getenv("DEEPAGENT_MAX_STEPS", "8"))
    DEEPAGENT_CRITIC_ROUNDS: int = int(os.getenv("DEEPAGENT_CRITIC_ROUNDS", "2"))
    DEEPAGENT_TIMEOUT_SECS: int = int(os.getenv("DEEPAGENT_TIMEOUT_SECS", "60"))

    # Vector DB Config - Pinecone only
    @property
    def VECTOR_DB_CONFIG(self) -> Dict[str, Any]:
        return {
            "provider": self.VECTOR_DB_PROVIDER,
            "pinecone_api_key": self.PINECONE_API_KEY,
            "pinecone_environment": self.PINECONE_ENVIRONMENT,
            "pinecone_index_name": self.PINECONE_INDEX_NAME,
            "pinecone_namespace": self.PINECONE_NAMESPACE,
            "embedding_provider": self.DEFAULT_EMBEDDING_PROVIDER,
            "embedding_model": self.EMBEDDING_MODEL_NAME,
            "gemini_embedding_model": self.GEMINI_EMBEDDING_MODEL_NAME,
            "voyage_embedding_model": self.VOYAGE_EMBEDDING_MODEL_NAME,
            "voyage_api_key": self.VOYAGE_API_KEY,
        }

    # LLM Configs
    @property
    def LLM_CONFIGS(self) -> Dict[str, Any]:
        return {
            # API Keys
            "openai_api_key": self.OPENAI_API_KEY,
            "anthropic_api_key": self.ANTHROPIC_API_KEY,
            "google_api_key": self.GOOGLE_API_KEY,
            # Provider-specific models
            "anthropic_model": self.ANTHROPIC_MODEL_NAME,
            "gemini_model": self.GEMINI_MODEL_NAME,
            "openai_model": self.OPENAI_MODEL_NAME,
            # Default configurations
            "default_model": self.DEFAULT_LLM_MODEL,
            "fast_model": self.FAST_LLM_MODEL,
            "deep_model": self.DEEP_LLM_MODEL,
            "fallback_model": self.FALLBACK_LLM_MODEL
        }

    # 에이전트별 LLM 선호 모델 구성 (LLMManagerAgent에서 사용)
    @property
    def AGENT_MODEL_CONFIGS(self) -> Dict[str, Any]:
        """
        작업/에이전트 타입별로 선호하는 LLM 프로필 리스트를 정의합니다.

        - 값 예시:
          {
            "general": {"llm_models": ["gpt-4o", "claude-3-sonnet"]},
            "competency": {"llm_models": ["claude-3-opus", "gpt-4o"]},
            ...
          }
        """
        return {
            "general": {
                # 기본 대화/요약/일반 질의
                "llm_models": [self.ANTHROPIC_MODEL_NAME, self.GEMINI_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "competency": {
                # 역량 진단/분석은 정밀도 우선
                "llm_models": [self.ANTHROPIC_MODEL_NAME, self.OPENAI_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "recommendation": {
                # 개인화 추천: 창의성 + 추론 균형
                "llm_models": [self.OPENAI_MODEL_NAME, self.ANTHROPIC_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "search": {
                # 검색 후 요약: 속도 우선
                "llm_models": [self.GEMINI_MODEL_NAME, self.OPENAI_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "analytics": {
                # 리포트/지표 해석: 심화 분석 모델 우선
                "llm_models": [self.ANTHROPIC_MODEL_NAME, self.OPENAI_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "mission": {
                # 미션 매칭/캠페인 설명: 요약+추론
                "llm_models": [self.OPENAI_MODEL_NAME, self.ANTHROPIC_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "rag": {
                # RAG 응답 생성: 컨텍스트 처리 용량이 큰 모델 우선
                "llm_models": [self.OPENAI_MODEL_NAME, self.ANTHROPIC_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "deep_agents": {
                # Deep Agents 내부에서 사용할 심화 모델
                "llm_models": [self.ANTHROPIC_MODEL_NAME, self.OPENAI_MODEL_NAME],
                "vector_db": "pinecone"
            },
            "creator": {
                # 크리에이터 온보딩 평가
                "llm_models": [self.ANTHROPIC_MODEL_NAME, self.GEMINI_MODEL_NAME],
                "vector_db": "pinecone"
            },
        }

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_settings(self) -> None:
        """필수 설정 및 경로 유효성 점검"""
        # 운영 모드에서는 DEBUG 강제 비활성화
        if self.ENV in ("prod", "production"):
            self.DEBUG = False  # type: ignore[assignment]
        # 필수 API 키 경고 (운영 시)
        if not self.DEBUG:
            if not self.OPENAI_API_KEY and not self.ANTHROPIC_API_KEY:
                # 운영환경에서 둘 다 비어있으면 경고 로그를 남길 수 있도록 raise 대신 ValueError 메시지 제공
                import logging
                logging.getLogger(__name__).warning(
                    "No LLM API keys configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY."
                )

        # ALLOWED_ORIGINS 파싱 안전성 확보 (JSON/CSV 혼용 지원)
        try:
            if isinstance(self.ALLOWED_ORIGINS, str) and self.ALLOWED_ORIGINS.strip().startswith("["):
                import json
                parsed = json.loads(self.ALLOWED_ORIGINS)
                if isinstance(parsed, list):
                    # 내부 표현은 CSV 문자열 유지, 접근은 allowed_origins_list 사용 권장
                    self.ALLOWED_ORIGINS = ",".join([str(o) for o in parsed])  # type: ignore[assignment]
        except Exception:
            # 실패 시 기존 CSV 파싱 경로 사용
            pass

        # 운영 환경에서는 CORS 화이트리스트 필수
        if self.ENV in ("prod", "production") and not self.allowed_origins_list:
            import logging
            logging.getLogger(__name__).warning(
                "ALLOWED_ORIGINS is empty in production. Set at least one allowed origin."
            )

        # SECRET_KEY 유효성 검사: 인증 활성화 시 필수
        try:
            import logging
            if self.ENABLE_AUTH and not self.SECRET_KEY:
                if self.DEBUG:
                    # 개발 모드에서는 고정 개발 키로 설정하고 경고
                    self.SECRET_KEY = "dev-secret-key"  # type: ignore[assignment]
                    logging.getLogger(__name__).warning(
                        "SECRET_KEY is not set. Using a development-only default. Do not use in production."
                    )
                else:
                    raise ValueError(
                        "SECRET_KEY is required when authentication is enabled. Set SECRET_KEY environment variable."
                    )
        except Exception:
            # 상위에서 처리되도록 예외는 숨기지 않음
            raise

        # Naver Cloud 배포 시 기본 키 존재 여부 안내(서버 배포용, 필수는 아님)
        try:
            import logging
            if (self.CLOUD_PROVIDER == "ncp") and (not self.NCLOUD_ACCESS_KEY_ID or not self.NCLOUD_SECRET_KEY):
                logging.getLogger(__name__).info(
                    "NCP credentials not set. If you use Naver Cloud SDK/services, set NCLOUD_ACCESS_KEY_ID/NCLOUD_SECRET_KEY."
                )
        except Exception:
            pass

        # Pinecone 설정 검증
        try:
            import logging
            if self.VECTOR_DB_PROVIDER == "pinecone" and not self.PINECONE_API_KEY:
                logging.getLogger(__name__).warning(
                    "PINECONE_API_KEY is not set. Vector search will be limited."
                )
        except Exception:
            pass


_settings = None


def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤 패턴)"""
    global _settings
    if _settings is None:
        _settings = Settings()
        _settings.validate_settings()
    return _settings
