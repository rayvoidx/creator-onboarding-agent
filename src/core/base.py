"""
AI Learning System Core Base Classes

DER-009에 따른 모듈화된 아키텍처의 기본 추상 클래스들을 정의합니다.
향후 연계 사업과 호환 가능한 확장 가능한 설계를 제공합니다.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseEntity(BaseModel):
    """모든 엔티티의 기본 클래스"""

    id: Optional[str] = Field(default=None, description="엔티티 고유 ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True
        json_encoders = {datetime: lambda dt: dt.isoformat()}


class BaseState(BaseModel):
    """LangGraph State의 기본 클래스"""

    user_id: Optional[str] = None
    session_id: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)

    def add_error(self, error: str) -> None:
        """에러 메시지를 추가합니다"""
        self.errors.append(error)
        logger.error(f"State error added: {error}")


class BaseService(ABC, Generic[T]):
    """서비스 레이어의 기본 추상 클래스"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config if config is not None else {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def process(self, data: T) -> T:
        """데이터를 처리하는 메인 메소드"""
        pass

    async def validate_input(self, data: T) -> bool:
        """입력 데이터를 검증합니다"""
        return True

    async def handle_error(self, error: Exception) -> Optional[T]:
        """에러를 처리합니다"""
        self.logger.error(f"Service error: {error}")
        return None


S = TypeVar("S", bound=BaseState)


class BaseAgent(ABC, Generic[S]):
    """AI 에이전트의 기본 추상 클래스"""

    def __init__(self, name: str, config: Optional[Dict[str, Any]] = None):
        self.name = name
        self.config = config if config is not None else {}
        self.logger = logging.getLogger(f"{self.__class__.__name__}.{name}")

    @abstractmethod
    async def execute(self, state: S) -> S:
        """에이전트의 주요 실행 로직"""
        pass

    async def pre_execute(self, state: S) -> S:
        """실행 전 처리"""
        self.logger.info(f"Agent {self.name} pre-execution started")
        return state

    async def post_execute(self, state: S) -> S:
        """실행 후 처리"""
        self.logger.info(f"Agent {self.name} post-execution completed")
        return state


class BaseTool(ABC):
    """도구의 기본 추상 클래스"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.logger = logging.getLogger(f"Tool.{name}")

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """도구를 실행합니다"""
        pass

    async def validate_parameters(self, **kwargs: Any) -> bool:
        """매개변수를 검증합니다"""
        return True


class BaseProcessor(ABC, Generic[T]):
    """데이터 처리기의 기본 추상 클래스"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"Processor.{name}")

    @abstractmethod
    async def process(self, data: T) -> T:
        """데이터를 처리합니다"""
        pass

    async def preprocess(self, data: T) -> T:
        """전처리"""
        return data

    async def postprocess(self, data: T) -> T:
        """후처리"""
        return data


class ModuleConfig(BaseModel):
    """모듈 설정 클래스"""

    module_name: str
    enabled: bool = True
    config: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[str] = Field(default_factory=list)
    version: str = "1.0.0"


class SystemHealth(BaseModel):
    """시스템 건강 상태"""

    status: str  # healthy, degraded, unhealthy
    modules: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    message: Optional[str] = None


class BaseRepository(ABC, Generic[T]):
    """저장소 패턴의 기본 추상 클래스"""

    @abstractmethod
    async def create(self, entity: T) -> T:
        """엔티티 생성"""
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """ID로 엔티티 조회"""
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        """엔티티 업데이트"""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """엔티티 삭제"""
        pass

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> List[T]:
        """엔티티 목록 조회"""
        pass
