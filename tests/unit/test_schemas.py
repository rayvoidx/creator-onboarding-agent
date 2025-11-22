from datetime import datetime
import pytest

from src.api.schemas.request_schemas import (
    CompetencyAssessmentRequest,
    RecommendationRequest,
    SearchRequest,
    AnalyticsRequest,
    MissionRecommendRequest,
)


def test_competency_assessment_request_valid():
    req = CompetencyAssessmentRequest(
        user_id="u1",
        session_id="s1",
        assessment_data={"domain": "childcare"},
    )
    assert req.user_id == "u1"
    assert req.session_id == "s1"


def test_competency_assessment_request_invalid_user():
    with pytest.raises(Exception):
        CompetencyAssessmentRequest(user_id=" ", session_id="s1", assessment_data={})


def test_recommendation_request_valid():
    req = RecommendationRequest(user_id="u2", session_id="s2", user_profile={"role": "teacher"})
    assert req.user_id == "u2"


def test_search_request_limit_bounds():
    req = SearchRequest(query="q", user_id="u3", session_id="s3", limit=5)
    assert req.limit == 5
    with pytest.raises(Exception):
        SearchRequest(query="q", user_id="u3", session_id="s3", limit=0)


def test_analytics_request_type_validation():
    req = AnalyticsRequest(user_id="u4", session_id="s4", report_type="learning_progress")
    assert req.report_type == "learning_progress"
    with pytest.raises(Exception):
        AnalyticsRequest(user_id="u4", session_id="s4", report_type="unknown")


def test_analytics_request_extended_types():
    # 확장 리포트 타입도 허용되는지 확인
    req = AnalyticsRequest(user_id="u5", session_id="s5", report_type="creator_mission_performance")
    assert req.report_type == "creator_mission_performance"
    req2 = AnalyticsRequest(user_id="u6", session_id="s6", report_type="reward_efficiency")
    assert req2.report_type == "reward_efficiency"


def test_external_sources_defaults():
    mission_req = MissionRecommendRequest(creator_id="creator-x")
    assert mission_req.external_sources == {}

    analytics_req = AnalyticsRequest(
        user_id="u7",
        session_id="s7",
        report_type="performance",
        external_sources={"search_query": "테스트"},
    )
    assert analytics_req.external_sources["search_query"] == "테스트"


