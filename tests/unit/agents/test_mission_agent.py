import pytest

from src.agents.mission_agent import MissionAgent, MissionRecommendationState
from src.data.models.mission_models import Mission, MissionRequirement


@pytest.mark.asyncio
async def test_mission_agent_basic_recommendation():
    agent = MissionAgent(config={"min_score_for_recommendation": 10.0, "top_k": 3})

    # 크리에이터 프로필 (온보딩 결과를 간단히 흉내)
    creator_profile = {
        "creator_id": "creator_1",
        "platform": "tiktok",
        "followers": 100_000,
        "engagement_rate": 0.05,  # 5%
        "posts_30d": 10,
        "reports_90d": 0,
    }
    onboarding_result = {
        "grade": "A",
        "tags": ["fashion", "beauty"],
        "risks": [],
    }

    missions = [
        Mission(
            id="m1",
            name="High tier content mission",
            reward_amount=150000.0,
            currency="KRW",
            requirement=MissionRequirement(
                min_followers=50_000,
                min_engagement_rate=0.02,
                min_posts_30d=5,
                min_grade="C",
                allowed_platforms=["tiktok"],
                disallow_high_reports=True,
                max_reports_90d=3,
                required_tags=["fashion"],
            ),
        ),
        Mission(
            id="m2",
            name="Too strict mission",
            reward_amount=500000.0,
            currency="KRW",
            requirement=MissionRequirement(
                min_followers=1_000_000,  # 너무 높아서 필터링되어야 함
                min_engagement_rate=0.1,
                min_posts_30d=30,
                min_grade="S",
                allowed_platforms=["instagram"],
                disallow_high_reports=True,
                max_reports_90d=1,
            ),
        ),
    ]

    state = MissionRecommendationState(
        user_id="creator_1",
        session_id="creator_1",
        creator_id="creator_1",
        creator_profile=creator_profile,
        onboarding_result=onboarding_result,
        missions=missions,
    )

    result_state = await agent.execute(state)

    # 첫 번째 미션은 추천 리스트에 포함되고, 두 번째 미션은 필터링되어야 한다.
    assert result_state.errors == []
    assert len(result_state.recommendations) == 1
    rec = result_state.recommendations[0]
    assert rec.mission_id == "m1"
    assert rec.creator_id == "creator_1"
    assert rec.score >= 10.0
    assert any("참여율이 미션 요구 조건을 충족합니다." in r for r in rec.reasons)


@pytest.mark.asyncio
async def test_mission_agent_risk_and_category_filters():
    agent = MissionAgent(config={"min_score_for_recommendation": 0.0, "top_k": 5})

    creator_profile = {
        "creator_id": "creator_risk",
        "platform": "instagram",
        "followers": 200_000,
        "engagement_rate": 0.06,
        "posts_30d": 15,
        "reports_90d": 4,  # 높은 신고 이력
        "category": "beauty",
        "completed_missions": 5,
        "avg_quality_score": 85,
        "current_active_missions": 1,
        "recent_mission_types": [],
    }
    onboarding_result = {
        "grade": "B",
        "tags": ["beauty"],
        "risks": ["high_reports"],
    }

    missions = [
        Mission(
            id="safe_mission",
            name="Beauty campaign",
            reward_amount=120000.0,
            currency="KRW",
            requirement=MissionRequirement(
                min_followers=100_000,
                min_engagement_rate=0.03,
                min_posts_30d=5,
                min_grade="C",
                allowed_platforms=["instagram"],
                disallow_high_reports=False,
                allowed_categories=["beauty"],
                exclude_risks=["low_engagement"],
                max_reports_90d=5,
                required_tags=["beauty"],
            ),
        ),
        Mission(
            id="strict_mission",
            name="Strict risk mission",
            reward_amount=90000.0,
            currency="KRW",
            requirement=MissionRequirement(
                min_followers=50_000,
                min_engagement_rate=0.02,
                min_posts_30d=3,
                min_grade="B",
                allowed_platforms=["instagram"],
                disallow_high_reports=True,
                excluded_categories=["beauty"],
                exclude_risks=["high_reports"],
                max_reports_90d=2,
            ),
        ),
    ]

    state = MissionRecommendationState(
        user_id="creator_risk",
        session_id="creator_risk",
        creator_id="creator_risk",
        creator_profile=creator_profile,
        onboarding_result=onboarding_result,
        missions=missions,
    )

    result_state = await agent.execute(state)

    # 첫 번째 미션은 조건을 충족하고, 두 번째 미션은 리스크/카테고리 조건으로 제외되어야 함
    rec_ids = [rec.mission_id for rec in result_state.recommendations]
    assert "safe_mission" in rec_ids
    assert "strict_mission" not in rec_ids
