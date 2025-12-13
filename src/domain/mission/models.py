"""Mission recommendation domain models."""

from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime

from pydantic import BaseModel, Field


class MissionType(str, Enum):
    """미션 유형"""

    CONTENT = "content"  # 콘텐츠 제작
    TRAFFIC = "traffic"  # 링크 클릭, 방문 유도
    CONVERSION = "conversion"  # 가입/구매 등 전환
    LIVE = "live"  # 라이브 방송
    OTHER = "other"


class RewardType(str, Enum):
    """보상 구조"""

    FIXED = "fixed"  # 정액
    PERFORMANCE = "performance"  # 성과 기반 (CPC/CPA 등)
    HYBRID = "hybrid"  # 기본 + 성과


class MissionRequirement(BaseModel):
    """미션 수행을 위한 요구 조건"""

    min_followers: int = Field(0, ge=0, description="최소 팔로워 수")
    max_followers: Optional[int] = Field(
        default=None, ge=0, description="최대 팔로워 수 (마이크로 타겟팅용)"
    )
    min_engagement_rate: float = Field(
        0.0, ge=0.0, le=1.0, description="최소 참여율 (0~1 스케일)"
    )
    min_posts_30d: int = Field(0, ge=0, description="최근 30일 최소 게시물 수")
    min_grade: str = Field("C", description="최소 등급 (S/A/B/C, 대소문자 무시)")
    allowed_platforms: List[str] = Field(
        default_factory=list, description="허용 플랫폼 (소문자: tiktok, instagram 등)"
    )
    disallow_high_reports: bool = Field(
        True, description="신고가 많은 크리에이터 제외 여부"
    )
    max_reports_90d: int = Field(
        2, ge=0, description="최근 90일 최대 신고 수 (이상이면 제외)"
    )
    allowed_categories: List[str] = Field(
        default_factory=list, description="허용 카테고리 (뷰티, 푸드 등)"
    )
    excluded_categories: List[str] = Field(
        default_factory=list, description="제외 카테고리"
    )
    exclude_risks: List[str] = Field(
        default_factory=list, description="제외할 리스크 태그 (high_reports 등)"
    )
    required_tags: List[str] = Field(
        default_factory=list, description="필수 태그(카테고리/도메인 등)"
    )


class Mission(BaseModel):
    """캠페인/미션 정의"""

    id: str
    name: str
    description: Optional[str] = None
    type: MissionType = MissionType.CONTENT
    reward_type: RewardType = RewardType.FIXED
    reward_amount: Optional[float] = Field(
        None, ge=0.0, description="기본 보상 금액 (있다면)"
    )
    currency: str = Field("KRW", description="보상 통화 코드")
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    requirement: MissionRequirement = Field(default_factory=MissionRequirement)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MissionAssignmentStatus(str, Enum):
    """미션 할당/진행 상태"""

    RECOMMENDED = "recommended"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class MissionAssignment(BaseModel):
    """크리에이터에게 추천/할당된 미션 인스턴스"""

    id: str
    mission_id: str
    creator_id: str
    status: MissionAssignmentStatus = MissionAssignmentStatus.RECOMMENDED
    score: float = Field(
        0.0, ge=0.0, le=100.0, description="미션과 크리에이터의 적합도 점수 (0~100)"
    )
    reasons: List[str] = Field(default_factory=list, description="추천/할당 사유")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
