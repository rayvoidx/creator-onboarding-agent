import pytest
from src.agents.creator_onboarding_agent import CreatorOnboardingAgent


@pytest.mark.asyncio
async def test_creator_scoring_basic():
    agent = CreatorOnboardingAgent()
    req = {
        "platform": "tiktok",
        "handle": "sample_creator",
        "metrics": {
            "followers": 250000,
            "avg_likes": 8000,
            "avg_comments": 300,
            "posts_30d": 20,
            "brand_fit": 0.7,
            "reports_90d": 0,
        },
    }
    res = await agent.execute(req)
    assert res.success is True
    assert res.platform == "tiktok"
    assert res.handle == "sample_creator"
    assert 0 <= res.score <= 100
    assert res.grade in {"S", "A", "B", "C"}

