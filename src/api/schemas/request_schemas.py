"""API 요청 스키마"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class CompetencyAssessmentRequest(BaseModel):
    """역량진단 요청"""
    user_id: str = Field(..., min_length=1, max_length=100, description="사용자 ID")
    session_id: str = Field(..., min_length=1, max_length=100, description="세션 ID")
    assessment_data: Dict[str, Any] = Field(default_factory=dict, description="진단 데이터")

    @field_validator('user_id', 'session_id')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """빈 문자열 검증"""
        if not v or not v.strip():
            raise ValueError("필드는 비어있을 수 없습니다")
        return v.strip()


class RecommendationRequest(BaseModel):
    """추천 요청"""
    user_id: str = Field(..., min_length=1, max_length=100, description="사용자 ID")
    session_id: Optional[str] = Field(None, max_length=100, description="세션 ID")
    user_profile: Dict[str, Any] = Field(default_factory=dict, description="사용자 프로필")
    learning_preferences: Dict[str, Any] = Field(default_factory=dict, description="학습 선호도")
    competency_data: Dict[str, Any] = Field(default_factory=dict, description="역량 데이터")

    @field_validator('user_id')
    @classmethod
    def validate_user_id(cls, v: str) -> str:
        """사용자 ID 검증"""
        if not v or not v.strip():
            raise ValueError("사용자 ID는 비어있을 수 없습니다")
        return v.strip()


class SearchRequest(BaseModel):
    """검색 요청"""
    query: str = Field(..., min_length=1, max_length=500, description="검색 쿼리")
    user_id: str = Field(..., min_length=1, max_length=100, description="사용자 ID")
    session_id: Optional[str] = Field(None, max_length=100, description="세션 ID")
    filters: Dict[str, Any] = Field(default_factory=dict, description="필터")
    limit: int = Field(10, ge=1, le=100, description="결과 개수")

    @field_validator('query', 'user_id')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """빈 문자열 검증"""
        if not v or not v.strip():
            raise ValueError("필드는 비어있을 수 없습니다")
        return v.strip()


class AnalyticsRequest(BaseModel):
    """분석 요청"""
    user_id: str = Field(..., min_length=1, max_length=100, description="사용자 ID")
    session_id: Optional[str] = Field(None, max_length=100, description="세션 ID")
    report_type: str = Field(..., min_length=1, max_length=50, description="리포트 유형")
    date_range: Dict[str, str] = Field(default_factory=dict, description="날짜 범위")
    filters: Dict[str, Any] = Field(default_factory=dict, description="필터")
    external_sources: Dict[str, Any] = Field(default_factory=dict, description="외부 데이터 소스 설정 (MCP 등)")

    @field_validator('user_id', 'report_type')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """빈 문자열 검증"""
        if not v or not v.strip():
            raise ValueError("필드는 비어있을 수 없습니다")
        return v.strip()

    @field_validator('report_type')
    @classmethod
    def validate_report_type(cls, v: str) -> str:
        """리포트 유형 검증"""
        allowed_types = [
            'competency',
            'learning_progress',
            'recommendations',
            'engagement',
            'performance',
            # 확장 타입 (크리에이터/미션/보상 인사이트용)
            'creator_mission_performance',
            'reward_efficiency',
        ]
        if v.strip().lower() not in allowed_types:
            raise ValueError(f"리포트 유형은 다음 중 하나여야 합니다: {', '.join(allowed_types)}")
        return v.strip().lower()


class CreatorEvaluationRequest(BaseModel):
    """Creator evaluation request"""
    platform: str = Field(..., description="tiktok|instagram|youtube 등")
    handle: str = Field(..., min_length=1, max_length=100, description="creator handle or id")
    profile_url: Optional[str] = Field(None, description="public profile url")
    metrics: Dict[str, Any] = Field(default_factory=dict, description="optional known metrics (followers, posts_30d, avg_likes, brand_fit, reports_90d)")

    @field_validator('platform', 'handle')
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("필드는 비어있을 수 없습니다")
        return v.strip()


class MissionCandidate(BaseModel):
    """미션 후보 입력"""

    id: str
    name: str
    description: Optional[str] = None
    type: str = "content"
    reward_type: str = "fixed"
    reward_amount: Optional[float] = None
    currency: str = "KRW"
    requirement: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MissionRecommendRequest(BaseModel):
    """미션 추천 요청"""

    creator_id: str = Field(..., min_length=1, max_length=100, description="크리에이터 ID")
    creator_profile: Dict[str, Any] = Field(
        default_factory=dict, description="크리에이터 메트릭/프로필 (followers, engagement_rate 등)"
    )
    onboarding_result: Dict[str, Any] = Field(
        default_factory=dict, description="CreatorOnboardingAgent 평가 결과"
    )
    missions: List[MissionCandidate] = Field(
        default_factory=list, description="추천 후보 미션 리스트"
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict, description="추가 필터 (예: 최소 점수, 타입 등)"
    )
    external_sources: Dict[str, Any] = Field(
        default_factory=dict, description="외부 데이터 소스 설정 (MCP 등)"
    )

    @field_validator("creator_id")
    @classmethod
    def validate_creator_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("creator_id는 비어있을 수 없습니다")
        return v.strip()
