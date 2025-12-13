"""Competency assessment models"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class CompetencyLevel(str, Enum):
    """역량 수준"""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CompetencyDomain(str, Enum):
    """역량 도메인"""

    CHILDCARE_POLICY = "childcare_policy"
    EDUCATION = "education"
    TECHNOLOGY = "technology"
    MANAGEMENT = "management"
    RESEARCH = "research"
    COMMUNICATION = "communication"


class SkillGap(BaseModel):
    """역량 격차"""

    skill_name: str
    current_level: CompetencyLevel
    target_level: CompetencyLevel
    priority: str = "medium"  # low, medium, high
    recommendations: List[str] = Field(default_factory=list)


class LearningPath(BaseModel):
    """학습 경로"""

    id: str
    title: str
    description: Optional[str] = None
    domain: CompetencyDomain
    target_level: CompetencyLevel
    estimated_hours: Optional[int] = None
    modules: List[Dict[str, Any]] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)


class CompetencyQuestion(BaseModel):
    """역량진단 문항"""

    id: str  # Alias for question_id for backwards compatibility
    question_id: str
    question_text: str
    domain: CompetencyDomain
    competency_area: str = "general"  # 역량 영역
    difficulty: str = "medium"  # easy, medium, hard
    options: List[str] = Field(default_factory=list)
    correct_answer: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def __init__(self, **data):
        # id와 question_id 동기화
        if "id" in data and "question_id" not in data:
            data["question_id"] = data["id"]
        elif "question_id" in data and "id" not in data:
            data["id"] = data["question_id"]
        super().__init__(**data)


class UserResponse(BaseModel):
    """사용자 응답"""

    id: str  # Alias for response_id
    response_id: str
    question_id: str
    user_id: str
    answer: str
    response_value: Optional[float] = None  # 응답 값 (0-1 스케일)
    response_time: Optional[float] = None  # seconds
    confidence_score: Optional[float] = 0.5  # 신뢰도 점수
    is_correct: Optional[bool] = None
    timestamp: datetime = Field(default_factory=datetime.now)

    def __init__(self, **data):
        # id와 response_id 동기화
        if "id" in data and "response_id" not in data:
            data["response_id"] = data["id"]
        elif "response_id" in data and "id" not in data:
            data["id"] = data["response_id"]
        super().__init__(**data)


class CompetencyProfile(BaseModel):
    """역량 프로필"""

    user_id: str
    assessed_at: datetime
    domain: CompetencyDomain
    overall_level: CompetencyLevel
    skill_levels: Dict[str, CompetencyLevel] = Field(default_factory=dict)
    skill_gaps: List[SkillGap] = Field(default_factory=list)
    recommended_paths: List[LearningPath] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
