"""API 응답 스키마"""

from typing import Dict, Any, List
from datetime import datetime
from pydantic import BaseModel


class CompetencyAssessmentResponse(BaseModel):
    """역량진단 응답"""

    success: bool
    assessment_id: str
    user_id: str
    analysis_result: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    performance_metrics: Dict[str, Any]
    timestamp: datetime


class RecommendationResponse(BaseModel):
    """추천 응답"""

    success: bool
    user_id: str
    recommendations: List[Dict[str, Any]]
    confidence_score: float
    reasoning: str
    timestamp: datetime


class SearchResponse(BaseModel):
    """검색 응답"""

    success: bool
    query: str
    results: List[Dict[str, Any]]
    total_count: int
    search_time: float
    timestamp: datetime


class AnalyticsResponse(BaseModel):
    """분석 응답"""

    success: bool
    report_id: str
    report_type: str
    user_id: str
    report_data: Dict[str, Any]
    insights: List[str]
    recommendations: List[Dict[str, Any]]
    timestamp: datetime


class HealthCheckResponse(BaseModel):
    """헬스 체크 응답"""

    status: str
    timestamp: datetime
    components: Dict[str, str]
    version: str


class CreatorEvaluationResponse(BaseModel):
    """Creator evaluation response"""

    success: bool
    platform: str
    handle: str
    decision: str
    grade: str
    score: float
    score_breakdown: Dict[str, float]
    tags: List[str]
    risks: List[str]
    report: str
    raw_profile: Dict[str, Any]
    timestamp: datetime


class MissionRecommendationItem(BaseModel):
    """단일 미션 추천 항목"""

    mission_id: str
    mission_name: str
    mission_type: str
    reward_type: str
    score: float
    reasons: List[str]
    metadata: Dict[str, Any]


class MissionRecommendationResponse(BaseModel):
    """미션 추천 응답"""

    success: bool
    creator_id: str
    recommendations: List[MissionRecommendationItem]
    timestamp: datetime
