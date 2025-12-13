import pytest

from src.agents.creator_onboarding_agent import CreatorOnboardingAgent
from src.agents.mission_agent import MissionAgent, MissionRecommendationState
from src.data.models.mission_models import Mission, MissionRequirement


@pytest.mark.asyncio
async def test_creator_onboarding_to_mission_recommendation_flow():
    # 1) Creator 온보딩 평가 실행
    onboarding_agent = CreatorOnboardingAgent()
    onboarding_request = {
        "platform": "tiktok",
        "handle": "sample_creator",
        "metrics": {
            "followers": 250_000,
            "avg_likes": 8_000,
            "avg_comments": 300,
            "posts_30d": 20,
            "brand_fit": 0.7,
            "reports_90d": 0,
        },
    }
    onboarding_result = await onboarding_agent.execute(onboarding_request)

    assert onboarding_result.success is True
    assert onboarding_result.platform == "tiktok"
    assert onboarding_result.handle == "sample_creator"

    # 2) 온보딩 결과 + 프로필을 기반으로 미션 후보 구성
    creator_profile = dict(onboarding_result.raw_profile)
    creator_profile.update(
        {
            "platform": onboarding_result.platform,
            "grade": onboarding_result.grade,
            "tags": onboarding_result.tags,
            "risks": onboarding_result.risks,
        }
    )

    mission = Mission(
        id="mission_1",
        name="테스트 캠페인 미션",
        requirement=MissionRequirement(
            min_followers=0,
            min_engagement_rate=0.0,
            min_posts_30d=0,
            min_grade="C",
            allowed_platforms=[],
        ),
        metadata={"test_case": True},
    )

    # 3) MissionAgent를 통해 미션 추천 실행
    mission_state = MissionRecommendationState(
        user_id="creator_1",
        session_id="session_1",
        creator_id="creator_1",
        creator_profile=creator_profile,
        onboarding_result={
            "grade": onboarding_result.grade,
            "tags": onboarding_result.tags,
            "risks": onboarding_result.risks,
        },
        missions=[mission],
    )

    mission_agent = MissionAgent(config={"min_score_for_recommendation": 0.0})
    result_state = await mission_agent.execute(mission_state)

    # 4) 온보딩 결과를 활용해 최소 1개 이상의 미션이 추천되는지 확인
    assert result_state.recommendations is not None
    assert len(result_state.recommendations) >= 1
