"""
크리에이터 프로필 이력 추적 모델
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class CreatorSnapshot(BaseModel):
    """특정 시점의 크리에이터 상태 스냅샷"""

    id: str
    creator_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # 플랫폼 정보
    platform: str
    handle: str

    # 메트릭
    followers: int
    avg_likes: int
    avg_comments: int
    posts_30d: int
    engagement_rate: float

    # 평가 결과
    grade: Optional[str] = None
    score: Optional[float] = None
    decision: Optional[str] = None  # accept, hold, reject
    tags: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)

    # 추가 메타데이터
    brand_fit: float = 0.0
    reports_90d: int = 0
    category: Optional[str] = None

    class Config:
        from_attributes = True


class CreatorHistoryEntry(BaseModel):
    """크리에이터 이력 항목"""

    id: str
    creator_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # 변경 유형
    change_type: str  # evaluation, metric_update, mission_complete, etc.
    description: str

    # 변경 전후 값
    previous_snapshot_id: Optional[str] = None
    current_snapshot_id: Optional[str] = None

    # 메트릭 변화
    metrics_delta: Dict[str, Any] = Field(default_factory=dict)

    # 관련 미션 정보
    mission_id: Optional[str] = None
    mission_name: Optional[str] = None

    class Config:
        from_attributes = True


class CreatorTrend(BaseModel):
    """크리에이터 트렌드 분석"""

    creator_id: str
    period_start: datetime
    period_end: datetime

    # 팔로워 트렌드
    followers_start: int
    followers_end: int
    followers_change: int
    followers_change_pct: float

    # 참여율 트렌드
    engagement_start: float
    engagement_end: float
    engagement_change: float
    engagement_change_pct: float

    # 점수 트렌드
    score_start: Optional[float] = None
    score_end: Optional[float] = None
    score_change: Optional[float] = None

    # 등급 변화
    grade_start: Optional[str] = None
    grade_end: Optional[str] = None
    grade_improved: bool = False

    # 완료한 미션 수
    missions_completed: int = 0

    # 트렌드 요약
    trend_summary: str = ""  # "improving", "stable", "declining"


class CreatorHistoryQuery(BaseModel):
    """크리에이터 이력 조회 필터"""

    creator_id: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    change_type: Optional[str] = None
    limit: int = 100
    offset: int = 0


class CreatorHistoryResponse(BaseModel):
    """크리에이터 이력 응답"""

    creator_id: str
    entries: List[CreatorHistoryEntry]
    snapshots: List[CreatorSnapshot]
    trend: Optional[CreatorTrend] = None
    total: int
