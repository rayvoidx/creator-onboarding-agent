# Mission Domain Specification

크리에이터 미션/캠페인 시스템의 도메인 모델과 추천 로직을 정의합니다.

---

## 1. 미션 개념 정의

### 1.1 미션(Mission)이란?
크리에이터가 브랜드/플랫폼을 위해 수행하는 특정 활동 단위입니다. 미션 완료 시 보상이 지급됩니다.

### 1.2 캠페인(Campaign)과의 관계
- **캠페인**: 마케팅 목표를 달성하기 위한 상위 프로젝트
- **미션**: 캠페인 내에서 크리에이터가 수행하는 개별 태스크
- 1개 캠페인 = N개 미션

---

## 2. 미션 타입 정의

### 2.1 콘텐츠 제작 (Content Creation)

| 서브타입 | 설명 | 난이도 | 기본 보상 범위 |
|----------|------|--------|----------------|
| `short_video` | 15-60초 숏폼 영상 | 중 | 50,000 - 200,000원 |
| `long_video` | 3분 이상 롱폼 영상 | 상 | 200,000 - 1,000,000원 |
| `image_post` | 이미지 포스트 | 하 | 30,000 - 100,000원 |
| `carousel` | 다중 이미지 슬라이드 | 중 | 50,000 - 150,000원 |
| `story` | 24시간 스토리 | 하 | 20,000 - 80,000원 |
| `reels` | 릴스/쇼츠 특화 | 중 | 50,000 - 200,000원 |

### 2.2 참여형 (Engagement)

| 서브타입 | 설명 | 난이도 | 기본 보상 범위 |
|----------|------|--------|----------------|
| `live_stream` | 라이브 방송 | 상 | 100,000 - 500,000원 |
| `comment_engagement` | 댓글 참여 유도 | 하 | 10,000 - 50,000원 |
| `challenge_participation` | 챌린지 참여 | 중 | 30,000 - 150,000원 |
| `collaboration` | 다른 크리에이터와 협업 | 상 | 150,000 - 500,000원 |

### 2.3 트래픽 유도 (Traffic)

| 서브타입 | 설명 | 난이도 | 기본 보상 범위 |
|----------|------|--------|----------------|
| `link_click` | 링크 클릭 유도 | 하 | 10,000 - 50,000원 |
| `app_install` | 앱 설치 유도 | 중 | 50,000 - 200,000원 |
| `sign_up` | 회원가입 유도 | 중 | 30,000 - 150,000원 |
| `purchase` | 구매 전환 | 상 | 성과 기반 |

### 2.4 브랜딩 (Branding)

| 서브타입 | 설명 | 난이도 | 기본 보상 범위 |
|----------|------|--------|----------------|
| `brand_mention` | 브랜드 언급 | 하 | 20,000 - 100,000원 |
| `product_review` | 제품 리뷰 | 중 | 50,000 - 300,000원 |
| `unboxing` | 언박싱 콘텐츠 | 중 | 50,000 - 200,000원 |
| `tutorial` | 사용법 튜토리얼 | 상 | 100,000 - 400,000원 |

---

## 3. 미션 난이도 체계

| 난이도 | 설명 | 예상 소요시간 | 최소 등급 |
|--------|------|---------------|-----------|
| **하 (Easy)** | 간단한 참여/게시 | 30분 이내 | C |
| **중 (Medium)** | 기획+제작 필요 | 1-3시간 | B |
| **상 (Hard)** | 고품질 콘텐츠 제작 | 3시간 이상 | A |
| **특급 (Expert)** | 전문적 기획+협업 | 1일 이상 | S |

---

## 4. 보상 구조

### 4.1 보상 타입

| 타입 | 설명 | 적용 사례 |
|------|------|-----------|
| `fixed` | 고정 보상 | 콘텐츠 제작 완료 시 |
| `performance` | 성과 기반 | 클릭/전환 수에 따라 |
| `hybrid` | 고정 + 성과 | 기본 보상 + 성과 보너스 |
| `tiered` | 단계별 | 목표 달성률에 따라 차등 |

### 4.2 성과 보상 계산 예시

```
hybrid 보상 = 고정보상 + (단위성과보상 × 성과량)

예: 기본 50,000원 + (100원 × 클릭수)
    - 1,000 클릭 달성 시: 50,000 + 100,000 = 150,000원
```

### 4.3 단계별 보상 구조

| 달성률 | 보상 비율 |
|--------|-----------|
| < 50% | 0% (미지급) |
| 50-80% | 50% |
| 80-100% | 100% |
| > 100% | 100% + 보너스 |

---

## 5. 데이터 모델 스펙

### 5.1 Mission (미션)

```python
class Mission:
    # 기본 정보
    mission_id: str              # 미션 고유 ID
    campaign_id: str             # 소속 캠페인 ID
    title: str                   # 미션 제목
    description: str             # 미션 상세 설명

    # 타입 및 난이도
    mission_type: MissionType    # 미션 타입 (content_creation, engagement, traffic, branding)
    mission_subtype: str         # 서브타입 (short_video, live_stream 등)
    difficulty: Difficulty       # 난이도 (easy, medium, hard, expert)

    # 기간
    start_date: datetime         # 시작일
    end_date: datetime           # 종료일
    submission_deadline: datetime # 제출 마감일

    # 목표 지표
    target_metrics: TargetMetrics

    # 보상
    reward_structure: RewardStructure

    # 요구사항
    requirements: MissionRequirement

    # 상태
    status: MissionStatus        # draft, active, paused, completed, cancelled
    slots_total: int             # 총 모집 인원
    slots_filled: int            # 현재 배정 인원

    # 메타데이터
    brand_id: str                # 브랜드 ID
    category: str                # 카테고리 (뷰티, 푸드, 테크 등)
    tags: List[str]              # 태그
    created_at: datetime
    updated_at: datetime
```

### 5.2 TargetMetrics (목표 지표)

```python
class TargetMetrics:
    # 도달 목표
    target_reach: Optional[int]           # 목표 도달 수
    target_impressions: Optional[int]     # 목표 노출 수

    # 참여 목표
    target_engagement: Optional[int]      # 목표 참여 수
    target_engagement_rate: Optional[float] # 목표 참여율 (%)

    # 전환 목표
    target_clicks: Optional[int]          # 목표 클릭 수
    target_conversions: Optional[int]     # 목표 전환 수
    target_conversion_rate: Optional[float] # 목표 전환율 (%)

    # 콘텐츠 목표
    min_content_count: int = 1            # 최소 콘텐츠 수
    min_content_duration: Optional[int]   # 최소 영상 길이 (초)
    required_hashtags: List[str] = []     # 필수 해시태그
    required_mentions: List[str] = []     # 필수 멘션
```

### 5.3 MissionRequirement (미션 요구사항)

```python
class MissionRequirement:
    # 크리에이터 자격 조건
    min_followers: int = 0               # 최소 팔로워 수
    max_followers: Optional[int] = None  # 최대 팔로워 수 (마이크로 타겟팅)
    min_engagement_rate: float = 0.0     # 최소 참여율 (%)
    min_grade: str = "C"                 # 최소 등급 (S/A/B/C)

    # 플랫폼 조건
    allowed_platforms: List[str] = []    # 허용 플랫폼 (빈 리스트 = 모든 플랫폼)

    # 카테고리 조건
    allowed_categories: List[str] = []   # 허용 카테고리
    excluded_categories: List[str] = []  # 제외 카테고리

    # 리스크 조건
    exclude_risks: List[str] = []        # 제외할 리스크 태그 (high_reports 등)
    max_reports_90d: int = 2             # 최근 90일 최대 신고 수

    # 이력 조건
    min_completed_missions: int = 0      # 최소 완료 미션 수
    min_avg_quality_score: float = 0.0   # 최소 평균 품질 점수

    # 콘텐츠 조건
    required_equipment: List[str] = []   # 필요 장비 (카메라, 마이크 등)
    required_skills: List[str] = []      # 필요 스킬 (편집, 촬영 등)
```

### 5.4 RewardStructure (보상 구조)

```python
class RewardStructure:
    # 보상 타입
    reward_type: RewardType           # fixed, performance, hybrid, tiered

    # 고정 보상
    fixed_amount: int = 0             # 고정 보상액 (원)

    # 성과 보상
    performance_metrics: str = ""     # 성과 기준 지표 (clicks, conversions 등)
    rate_per_unit: float = 0.0        # 단위당 보상액
    performance_cap: Optional[int] = None  # 성과 보상 상한

    # 단계별 보상
    tiers: List[RewardTier] = []      # 단계별 보상 정의

    # 보너스
    early_completion_bonus: int = 0   # 조기 완료 보너스
    quality_bonus: int = 0            # 품질 보너스
    overachievement_rate: float = 0.0 # 초과 달성 보너스율

class RewardTier:
    min_achievement: float            # 최소 달성률 (%)
    max_achievement: float            # 최대 달성률 (%)
    reward_rate: float                # 보상 비율 (%)
```

### 5.5 MissionAssignment (미션 배정)

```python
class MissionAssignment:
    # 기본 정보
    assignment_id: str               # 배정 ID
    mission_id: str                  # 미션 ID
    creator_id: str                  # 크리에이터 ID

    # 배정 정보
    assigned_at: datetime            # 배정 일시
    assigned_by: str                 # 배정자 (system, admin 등)
    assignment_reason: str           # 배정 이유 (추천 근거)
    match_score: float               # 매칭 점수 (0-100)

    # 상태
    status: AssignmentStatus         # pending, accepted, rejected, in_progress,
                                     # submitted, approved, completed, failed

    # 타임라인
    accepted_at: Optional[datetime]  # 수락 일시
    submitted_at: Optional[datetime] # 제출 일시
    completed_at: Optional[datetime] # 완료 일시

    # 성과
    actual_metrics: ActualMetrics    # 실제 달성 지표
    achievement_rate: float          # 달성률 (%)
    quality_score: float             # 품질 점수 (0-100)

    # 보상
    calculated_reward: int           # 계산된 보상액
    bonus_reward: int                # 보너스 보상액
    total_reward: int                # 총 보상액
    paid_at: Optional[datetime]      # 지급 일시

    # 피드백
    creator_feedback: Optional[str]  # 크리에이터 피드백
    brand_feedback: Optional[str]    # 브랜드 피드백
    rating: Optional[float]          # 평점 (1-5)
```

---

## 6. 미션 추천 로직

### 6.1 추천 원칙

1. **자격 충족**: 크리에이터가 미션 요구사항을 충족해야 함
2. **적합성 최대화**: 크리에이터-미션 간 매칭 점수 최대화
3. **다양성 확보**: 동일 크리에이터에게 다양한 미션 유형 추천
4. **공정성**: 모든 자격 크리에이터에게 기회 분배

### 6.2 자격 필터링 규칙

```python
def is_eligible(creator, mission):
    req = mission.requirements

    # 기본 자격 체크
    if creator.followers < req.min_followers:
        return False
    if req.max_followers and creator.followers > req.max_followers:
        return False
    if creator.engagement_rate < req.min_engagement_rate:
        return False
    if grade_rank(creator.grade) < grade_rank(req.min_grade):
        return False

    # 플랫폼 체크
    if req.allowed_platforms and creator.platform not in req.allowed_platforms:
        return False

    # 카테고리 체크
    if req.excluded_categories and creator.category in req.excluded_categories:
        return False

    # 리스크 체크
    for risk in creator.risks:
        if risk in req.exclude_risks:
            return False
    if creator.reports_90d > req.max_reports_90d:
        return False

    # 이력 체크
    if creator.completed_missions < req.min_completed_missions:
        return False
    if creator.avg_quality_score < req.min_avg_quality_score:
        return False

    return True
```

### 6.3 매칭 스코어링

```python
def calculate_match_score(creator, mission):
    score = 0.0
    weights = {
        'grade_fit': 0.25,
        'engagement_fit': 0.20,
        'category_fit': 0.20,
        'history_fit': 0.15,
        'availability_fit': 0.10,
        'diversity_bonus': 0.10
    }

    # 등급 적합도 (25%)
    grade_diff = grade_rank(creator.grade) - grade_rank(mission.requirements.min_grade)
    score += weights['grade_fit'] * min(grade_diff / 3, 1.0) * 100

    # 참여율 적합도 (20%)
    er_ratio = creator.engagement_rate / max(mission.requirements.min_engagement_rate, 0.01)
    score += weights['engagement_fit'] * min(er_ratio, 2.0) * 50

    # 카테고리 적합도 (20%)
    if creator.category in mission.requirements.allowed_categories:
        score += weights['category_fit'] * 100
    elif not mission.requirements.allowed_categories:
        score += weights['category_fit'] * 50

    # 이력 적합도 (15%)
    history_score = min(creator.completed_missions / 10, 1.0) * 50
    history_score += min(creator.avg_quality_score / 100, 1.0) * 50
    score += weights['history_fit'] * history_score

    # 가용성 (10%)
    if creator.current_active_missions < 3:
        score += weights['availability_fit'] * 100

    # 다양성 보너스 (10%)
    if mission.mission_type not in creator.recent_mission_types:
        score += weights['diversity_bonus'] * 100

    return min(score, 100)
```

### 6.4 등급별 추천 전략

| 크리에이터 등급 | 추천 전략 |
|----------------|-----------|
| **S** | 고예산/고난이도 미션 우선, VIP 브랜드 캠페인, 협업 미션 |
| **A** | 중-고난이도 미션, 다양한 유형 경험, 품질 중심 |
| **B** | 중난이도 미션, 실적 쌓기 중심, 성장 기회 |
| **C** | 저난이도 미션, 기본 요구사항만 충족, 신뢰도 구축 |

### 6.5 리스크 기반 제외 규칙

| 리스크 태그 | 제외 미션 유형 | 이유 |
|-------------|----------------|------|
| `high_reports` | 모든 미션 | 신고 이력으로 브랜드 리스크 |
| `low_engagement` | 성과 기반 미션 | 목표 달성 가능성 낮음 |
| `low_activity` | 긴급/단기 미션 | 응답/완료 지연 우려 |

---

## 7. 열거형 정의

```python
class MissionType(Enum):
    CONTENT_CREATION = "content_creation"
    ENGAGEMENT = "engagement"
    TRAFFIC = "traffic"
    BRANDING = "branding"

class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"

class RewardType(Enum):
    FIXED = "fixed"
    PERFORMANCE = "performance"
    HYBRID = "hybrid"
    TIERED = "tiered"

class MissionStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class AssignmentStatus(Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    COMPLETED = "completed"
    FAILED = "failed"
```

---

## 8. API 설계 참고

### 8.1 미션 추천 API

```
POST /api/v1/missions/recommend
Request:
{
    "creator_id": "creator_123",
    "limit": 5,
    "filters": {
        "mission_types": ["content_creation"],
        "min_reward": 50000,
        "max_difficulty": "medium"
    }
}

Response:
{
    "success": true,
    "recommendations": [
        {
            "mission_id": "mission_456",
            "match_score": 85.5,
            "recommendation_reason": "등급 적합, 높은 참여율, 관련 카테고리",
            "mission_summary": { ... }
        }
    ]
}
```

### 8.2 미션 배정 API

```
POST /api/v1/missions/{mission_id}/assign
Request:
{
    "creator_id": "creator_123",
    "assignment_reason": "추천 시스템 자동 배정"
}

Response:
{
    "success": true,
    "assignment_id": "assign_789",
    "status": "pending"
}
```
