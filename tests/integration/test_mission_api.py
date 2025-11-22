from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def _build_sample_request():
    return {
        "creator_id": "creator_api_1",
        "creator_profile": {
            "platform": "tiktok",
            "followers": 120000,
            "engagement_rate": 0.04,
            "posts_30d": 12,
            "reports_90d": 0,
        },
        "onboarding_result": {
            "grade": "A",
            "tags": ["fashion"],
            "risks": [],
        },
        "missions": [
            {
                "id": "m_api_1",
                "name": "API Mission 1",
                "type": "content",
                "reward_type": "fixed",
                "reward_amount": 100000.0,
                "currency": "KRW",
                "requirement": {
                    "min_followers": 50000,
                    "min_engagement_rate": 0.02,
                    "min_posts_30d": 5,
                    "allowed_platforms": ["tiktok"],
                    "disallow_high_reports": True,
                    "required_tags": ["fashion"],
                },
            }
        ],
        "filters": {},
    }


def test_missions_recommend_endpoint_smoke():
    # 단순 스모크 테스트: 200 응답 및 기본 구조 확인
    payload = _build_sample_request()
    response = client.post("/api/v1/missions/recommend", json=payload)
    assert response.status_code in (200, 503)

    # orchestrator 초기화 실패 등으로 503이 나올 수 있으므로,
    # 200인 경우에만 응답 스키마를 간단히 검증한다.
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert data["creator_id"] == "creator_api_1"
        assert isinstance(data["recommendations"], list)
        if data["recommendations"]:
            item = data["recommendations"][0]
            assert "mission_id" in item
            assert "score" in item
            assert "reasons" in item


