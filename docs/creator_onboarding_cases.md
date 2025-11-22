# Creator Onboarding 테스트 시나리오

본 문서는 다양한 입력 조합에 대해 예상되는 점수, 등급, 결정을 정리한 테스트 케이스 표입니다.

---

## 테스트 케이스 표

### 정상 케이스 (리스크 없음)

| ID | 케이스명 | followers | avg_likes | avg_comments | posts_30d | reports_90d | brand_fit | 예상 score | 예상 grade | 예상 decision | 비고 |
|----|----------|-----------|-----------|--------------|-----------|-------------|-----------|------------|------------|---------------|------|
| T01 | 메가 인플루언서 | 1,000,000 | 50,000 | 2,000 | 30 | 0 | 1.0 | 85-100 | S | accept | 모든 지표 최대 |
| T02 | 대형 인플루언서 | 800,000 | 30,000 | 1,000 | 25 | 0 | 0.8 | 75-85 | A | accept | 우수 크리에이터 |
| T03 | 중형 인플루언서 | 300,000 | 10,000 | 400 | 15 | 0 | 0.6 | 55-70 | B | accept | 양호 |
| T04 | 소형 마이크로 | 50,000 | 2,000 | 100 | 10 | 0 | 0.5 | 40-55 | C | accept | 기준 미달이나 승인 |
| T05 | 나노 인플루언서 | 10,000 | 500 | 50 | 8 | 0 | 0.3 | 30-45 | C | accept | 소규모 |
| T06 | 높은 ER 소형 | 50,000 | 3,000 | 200 | 20 | 0 | 0.7 | 50-65 | B/C | accept | 팔로워 적으나 참여율 높음 |
| T07 | 낮은 ER 대형 | 500,000 | 2,000 | 100 | 20 | 0 | 0.5 | 45-60 | C/B | accept | 팔로워 많으나 참여율 낮음 |

### 리스크 케이스

| ID | 케이스명 | followers | avg_likes | avg_comments | posts_30d | reports_90d | brand_fit | 예상 score | 예상 grade | 예상 decision | 리스크 태그 | 비고 |
|----|----------|-----------|-----------|--------------|-----------|-------------|-----------|------------|------------|---------------|-------------|------|
| T08 | 높은 신고 | 300,000 | 8,000 | 300 | 15 | 5 | 0.5 | 35-50 | C | **reject** | high_reports | 신고 이력으로 거절 |
| T09 | 낮은 참여율 | 200,000 | 200 | 20 | 15 | 0 | 0.5 | 25-40 | C | accept | low_engagement | ER < 0.2% |
| T10 | 낮은 활동성 | 300,000 | 10,000 | 400 | 2 | 0 | 0.5 | 45-60 | C/B | **hold** | low_activity | posts_30d < 4 |
| T11 | 복합 리스크 1 | 100,000 | 100 | 10 | 2 | 0 | 0.3 | 0-25 | C | **hold** | low_engagement, low_activity | 참여율+활동성 둘 다 낮음 |
| T12 | 복합 리스크 2 | 100,000 | 50 | 5 | 3 | 4 | 0.2 | 0-20 | C | **reject** | high_reports, low_engagement, low_activity | 모든 리스크 |
| T13 | 신고+낮은 점수 | 50,000 | 500 | 50 | 10 | 3 | 0.3 | 0-35 | C | **reject** | high_reports | 신고 경계값 |

### 경계값 테스트

| ID | 케이스명 | followers | avg_likes | avg_comments | posts_30d | reports_90d | brand_fit | 예상 score | 예상 grade | 예상 decision | 비고 |
|----|----------|-----------|-----------|--------------|-----------|-------------|-----------|------------|------------|---------------|------|
| T14 | 등급 경계 S/A | - | - | - | - | 0 | - | 84-86 | S or A | accept | 85점 경계 |
| T15 | 등급 경계 A/B | - | - | - | - | 0 | - | 69-71 | A or B | accept | 70점 경계 |
| T16 | 등급 경계 B/C | - | - | - | - | 0 | - | 54-56 | B or C | accept | 55점 경계 |
| T17 | 결정 경계 | - | - | - | - | 0 | - | 49-51 | C | accept/reject | 50점 경계 (reject 기준) |
| T18 | 신고 경계 | 300,000 | 8,000 | 300 | 15 | 2 | 0.5 | 50-65 | C/B | accept | reports_90d = 2 (3 미만) |
| T19 | 신고 경계 초과 | 300,000 | 8,000 | 300 | 15 | 3 | 0.5 | 35-50 | C | reject | reports_90d = 3 |
| T20 | ER 경계 | 100,000 | 150 | 25 | 15 | 0 | 0.5 | 30-45 | C | accept | ER ≈ 0.2% 경계 |
| T21 | 활동 경계 | 300,000 | 10,000 | 400 | 4 | 0 | 0.5 | 50-65 | C/B | accept | posts_30d = 4 (경계값) |
| T22 | 활동 경계 미만 | 300,000 | 10,000 | 400 | 3 | 0 | 0.5 | 45-60 | C/B | hold | posts_30d = 3 |

### 특수 케이스

| ID | 케이스명 | followers | avg_likes | avg_comments | posts_30d | reports_90d | brand_fit | 예상 score | 예상 grade | 예상 decision | 비고 |
|----|----------|-----------|-----------|--------------|-----------|-------------|-----------|------------|------------|---------------|------|
| T23 | 최소값 | 0 | 0 | 0 | 0 | 0 | 0.0 | 0 | C | reject | 모든 값 0 |
| T24 | 최대값 | 10,000,000 | 500,000 | 50,000 | 100 | 0 | 1.0 | 100 | S | accept | 극단적 높은 값 |
| T25 | 팔로워만 높음 | 1,000,000 | 100 | 10 | 1 | 0 | 0.0 | 15-30 | C | hold | 팔로워만 있고 나머지 저조 |
| T26 | 참여만 높음 | 10,000 | 1,000 | 100 | 30 | 0 | 1.0 | 55-70 | B | accept | 소규모지만 높은 참여 |
| T27 | Hold 후 Accept | 200,000 | 6,000 | 200 | 3 | 0 | 0.6 | 55-68 | B | hold | 점수 ≥ 70이면 accept인데 low_activity |

---

## 점수 계산 예시

### 케이스 T01: 메가 인플루언서
```
followers = 1,000,000
avg_likes = 50,000
avg_comments = 2,000
posts_30d = 30
reports_90d = 0
brand_fit = 1.0

engagement_rate = (50,000 + 4,000) / 1,000,000 = 5.4%
frequency = 30 / 30 = 1.0

s_followers = min(1,000,000 / 1,000,000, 0.4) = 0.4 → 40점
s_engage = min(0.054 × 10, 0.3) = 0.3 → 30점
s_freq = min(1.0, 0.15) = 0.15 → 15점
s_fit = min(1.0 × 0.15, 0.15) = 0.15 → 15점

base_score = 40 + 30 + 15 + 15 = 100점
패널티 = 0
최종 점수 = 100점 → S등급 → accept
```

### 케이스 T08: 높은 신고
```
followers = 300,000
avg_likes = 8,000
avg_comments = 300
posts_30d = 15
reports_90d = 5
brand_fit = 0.5

engagement_rate = (8,000 + 600) / 300,000 = 2.87%
frequency = 15 / 30 = 0.5

s_followers = min(300,000 / 1,000,000, 0.4) = 0.12 → 12점
s_engage = min(0.0287 × 10, 0.3) = 0.287 → 28.7점
s_freq = min(0.5, 0.15) = 0.15 → 15점
s_fit = min(0.5 × 0.15, 0.15) = 0.075 → 7.5점

base_score = 12 + 28.7 + 15 + 7.5 = 63.2점
패널티 = -15점 (high_reports)
최종 점수 = 48.2점 → C등급 → reject (high_reports OR score < 50)
```

### 케이스 T10: 낮은 활동성
```
followers = 300,000
avg_likes = 10,000
avg_comments = 400
posts_30d = 2
reports_90d = 0
brand_fit = 0.5

engagement_rate = (10,000 + 800) / 300,000 = 3.6%
frequency = 2 / 30 = 0.067

s_followers = 0.12 → 12점
s_engage = 0.3 → 30점
s_freq = min(0.067, 0.15) = 0.067 → 6.7점
s_fit = 0.075 → 7.5점

base_score = 12 + 30 + 6.7 + 7.5 = 56.2점
패널티 = -5점 (low_activity)
최종 점수 = 51.2점 → C등급
결정 = hold (low_activity in risks AND score < 70)
```

---

## 테스트 실행 가이드

### 단위 테스트 작성 시 고려사항

1. **점수 범위 허용**: 부동소수점 연산으로 정확한 값 대신 범위로 검증
2. **등급 확인**: 점수에 따른 등급이 올바른지 확인
3. **결정 로직**: 리스크 태그와 점수에 따른 결정이 올바른지 확인
4. **태그 부여**: 조건에 맞는 태그가 부여되는지 확인

### pytest 예시

```python
import pytest
from src.agents.creator_onboarding_agent import CreatorOnboardingAgent

@pytest.mark.asyncio
async def test_t01_mega_influencer():
    agent = CreatorOnboardingAgent()
    result = await agent.execute({
        "platform": "tiktok",
        "handle": "mega_star",
        "metrics": {
            "followers": 1_000_000,
            "avg_likes": 50_000,
            "avg_comments": 2_000,
            "posts_30d": 30,
            "reports_90d": 0,
            "brand_fit": 1.0
        }
    })

    assert result.success is True
    assert 85 <= result.score <= 100
    assert result.grade == "S"
    assert result.decision == "accept"
    assert "top_candidate" in result.tags
    assert len(result.risks) == 0

@pytest.mark.asyncio
async def test_t08_high_reports():
    agent = CreatorOnboardingAgent()
    result = await agent.execute({
        "platform": "instagram",
        "handle": "risky_creator",
        "metrics": {
            "followers": 300_000,
            "avg_likes": 8_000,
            "avg_comments": 300,
            "posts_30d": 15,
            "reports_90d": 5,
            "brand_fit": 0.5
        }
    })

    assert result.success is True
    assert 35 <= result.score <= 50
    assert result.grade == "C"
    assert result.decision == "reject"
    assert "high_reports" in result.risks

@pytest.mark.asyncio
async def test_t10_low_activity():
    agent = CreatorOnboardingAgent()
    result = await agent.execute({
        "platform": "tiktok",
        "handle": "inactive_creator",
        "metrics": {
            "followers": 300_000,
            "avg_likes": 10_000,
            "avg_comments": 400,
            "posts_30d": 2,
            "reports_90d": 0,
            "brand_fit": 0.5
        }
    })

    assert result.success is True
    assert result.decision == "hold"
    assert "low_activity" in result.risks
```

---

## 결정 로직 요약 플로우차트

```
┌─────────────────┐
│ 점수 계산 완료  │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│ high_reports in risks          │
│ OR score < 50?                 │
└────────┬────────────────┬──────┘
         │ Yes            │ No
         ▼                ▼
    ┌────────┐    ┌─────────────────────────┐
    │ REJECT │    │ low_activity in risks   │
    └────────┘    │ AND score < 70?         │
                  └─────────┬───────────┬───┘
                            │ Yes       │ No
                            ▼           ▼
                       ┌────────┐  ┌────────┐
                       │  HOLD  │  │ ACCEPT │
                       └────────┘  └────────┘
```

---

## 추가 태그 부여 로직

| 조건 | 부여 태그 |
|------|-----------|
| grade in (S, A) | `top_candidate` |
| `low_engagement` in risks | `needs_awareness_campaign` |
| `low_activity` in risks | `needs_activation` |
