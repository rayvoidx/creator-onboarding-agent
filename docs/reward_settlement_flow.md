# Reward & Settlement Flow

미션 수행부터 보상 정산까지의 전체 흐름을 정의합니다.

---

## 1. 전체 프로세스 개요

```
미션 배정 → 미션 수행 → 이벤트 기록 → 성과 집계 → 보상 계산 → 정산 처리 → 지급 완료
```

### 1.1 주요 단계

| 단계 | 설명 | 주체 |
|------|------|------|
| **배정** | 크리에이터에게 미션 할당 | 시스템/관리자 |
| **수행** | 크리에이터가 미션 활동 수행 | 크리에이터 |
| **기록** | 성과 이벤트 실시간 수집 | 시스템 |
| **집계** | 성과 데이터 집계 및 검증 | 시스템 |
| **계산** | 보상 금액 산출 | 시스템 |
| **정산** | 지급 처리 및 확정 | 시스템/재무 |
| **지급** | 실제 금액 송금 | 재무 |

---

## 2. 이벤트 기록 체계

### 2.1 기록 대상 이벤트

#### 노출/도달 이벤트 (Impression/Reach)

| 이벤트 | 설명 | 기록 시점 | 데이터 |
|--------|------|-----------|--------|
| `content_published` | 콘텐츠 게시 | 게시 즉시 | content_id, platform, timestamp |
| `impression` | 노출 발생 | 실시간 | view_id, user_id, duration |
| `reach` | 고유 도달 | 집계 시 | unique_users |
| `view_complete` | 영상 완료 시청 | 시청 완료 시 | completion_rate |

#### 참여 이벤트 (Engagement)

| 이벤트 | 설명 | 기록 시점 | 데이터 |
|--------|------|-----------|--------|
| `like` | 좋아요 | 액션 발생 시 | user_id, timestamp |
| `comment` | 댓글 | 작성 완료 시 | user_id, content_length |
| `share` | 공유 | 공유 완료 시 | user_id, share_platform |
| `save` | 저장 | 저장 시 | user_id |
| `follow` | 팔로우 | 팔로우 시 | user_id |

#### 전환 이벤트 (Conversion)

| 이벤트 | 설명 | 기록 시점 | 데이터 |
|--------|------|-----------|--------|
| `link_click` | 링크 클릭 | 클릭 시 | user_id, link_url, source |
| `page_view` | 랜딩페이지 조회 | 페이지 로드 시 | session_id, duration |
| `sign_up` | 회원가입 | 가입 완료 시 | user_id, method |
| `app_install` | 앱 설치 | 설치 완료 시 | device_id, os |
| `purchase` | 구매 | 결제 완료 시 | order_id, amount, items |
| `lead` | 리드 생성 | 폼 제출 시 | lead_id, form_data |

#### 미션 상태 이벤트 (Mission Status)

| 이벤트 | 설명 | 기록 시점 | 데이터 |
|--------|------|-----------|--------|
| `mission_accepted` | 미션 수락 | 수락 시 | assignment_id |
| `content_submitted` | 콘텐츠 제출 | 제출 시 | content_urls, notes |
| `content_approved` | 콘텐츠 승인 | 승인 시 | approver_id, quality_score |
| `content_rejected` | 콘텐츠 반려 | 반려 시 | reason, feedback |
| `mission_completed` | 미션 완료 | 완료 확정 시 | final_metrics |

### 2.2 이벤트 데이터 모델

```python
class PerformanceEvent:
    event_id: str              # 이벤트 고유 ID
    event_type: str            # 이벤트 타입
    assignment_id: str         # 미션 배정 ID
    mission_id: str            # 미션 ID
    creator_id: str            # 크리에이터 ID
    content_id: str            # 콘텐츠 ID (해당 시)
    user_id: Optional[str]     # 참여 사용자 ID

    timestamp: datetime        # 발생 시각
    platform: str              # 발생 플랫폼
    device_type: str           # 디바이스 유형

    metadata: Dict[str, Any]   # 이벤트별 추가 데이터

    # 전환 관련
    conversion_value: float    # 전환 가치 (구매액 등)
    attribution_source: str    # 어트리뷰션 소스

    # 검증
    is_valid: bool            # 유효성 여부
    validation_status: str    # pending, verified, fraud, excluded
```

### 2.3 이벤트 검증 규칙

#### 유효성 검증

| 검증 항목 | 규칙 | 처리 |
|----------|------|------|
| **중복 이벤트** | 동일 user_id + event_type + 1분 내 | 첫 번째만 인정 |
| **봇/사기 감지** | IP 패턴, 디바이스 핑거프린트 | 제외 처리 |
| **어트리뷰션 기간** | 클릭 후 7일 / 노출 후 1일 | 기간 외 제외 |
| **지역 필터** | 허용 국가 외 | 제외 처리 |
| **시간 필터** | 미션 기간 외 | 제외 처리 |

#### 품질 검증 (콘텐츠)

| 검증 항목 | 기준 | 영향 |
|----------|------|------|
| **가이드라인 준수** | 필수 해시태그, 멘션 포함 | 미포함 시 반려 |
| **콘텐츠 길이** | 최소 기준 충족 | 미충족 시 반려 |
| **브랜드 적합성** | 네거티브 요소 없음 | 위반 시 반려 |
| **품질 점수** | 수동/자동 평가 | 보너스 적용 |

---

## 3. 성과 집계

### 3.1 집계 주기

| 주기 | 용도 | 데이터 |
|------|------|--------|
| **실시간** | 대시보드, 모니터링 | 현재 누적치 |
| **시간별** | 트렌드 분석 | 시간대별 집계 |
| **일별** | 일일 리포트 | 일별 확정치 |
| **미션 종료 시** | 최종 정산 | 최종 확정치 |

### 3.2 집계 메트릭

```python
class AggregatedMetrics:
    assignment_id: str
    aggregation_period: str    # hourly, daily, final

    # 노출/도달
    total_impressions: int
    unique_reach: int
    avg_view_duration: float
    video_completion_rate: float

    # 참여
    total_likes: int
    total_comments: int
    total_shares: int
    total_saves: int
    new_followers: int
    engagement_rate: float

    # 전환
    total_clicks: int
    click_through_rate: float
    total_conversions: int
    conversion_rate: float
    total_revenue: float

    # 유효성
    valid_events_count: int
    excluded_events_count: int
    fraud_rate: float

    # 계산 기준
    aggregated_at: datetime
    is_final: bool
```

---

## 4. 보상 계산 로직

### 4.1 보상 계산 흐름

```
1. 성과 집계 확정
2. 보상 유형 확인 (fixed/performance/hybrid/tiered)
3. 기본 보상 계산
4. 조정 요소 적용 (보너스/패널티)
5. 최종 보상 확정
```

### 4.2 보상 유형별 계산

#### Fixed (고정 보상)

```python
def calculate_fixed(mission, metrics):
    if metrics.is_mission_completed:
        return mission.reward_structure.fixed_amount
    else:
        return 0
```

#### Performance (성과 기반)

```python
def calculate_performance(mission, metrics):
    rs = mission.reward_structure

    # 성과 지표에 따른 계산
    if rs.performance_metrics == "clicks":
        base = metrics.valid_clicks * rs.rate_per_unit
    elif rs.performance_metrics == "conversions":
        base = metrics.valid_conversions * rs.rate_per_unit
    elif rs.performance_metrics == "revenue":
        base = metrics.total_revenue * rs.rate_per_unit  # 수수료율

    # 상한 적용
    if rs.performance_cap:
        base = min(base, rs.performance_cap)

    return base
```

#### Hybrid (고정 + 성과)

```python
def calculate_hybrid(mission, metrics):
    fixed = calculate_fixed(mission, metrics)
    performance = calculate_performance(mission, metrics)
    return fixed + performance
```

#### Tiered (단계별)

```python
def calculate_tiered(mission, metrics):
    rs = mission.reward_structure
    achievement_rate = calculate_achievement_rate(mission, metrics)

    for tier in rs.tiers:
        if tier.min_achievement <= achievement_rate < tier.max_achievement:
            base_reward = rs.fixed_amount * tier.reward_rate
            return base_reward

    return 0  # 최소 달성률 미충족
```

### 4.3 달성률 계산

```python
def calculate_achievement_rate(mission, metrics):
    target = mission.target_metrics

    # 주요 목표 지표 기준
    if target.target_reach:
        return (metrics.unique_reach / target.target_reach) * 100
    elif target.target_clicks:
        return (metrics.total_clicks / target.target_clicks) * 100
    elif target.target_conversions:
        return (metrics.total_conversions / target.target_conversions) * 100
    elif target.target_engagement:
        return (metrics.total_engagement / target.target_engagement) * 100
    else:
        return 100 if metrics.is_mission_completed else 0
```

### 4.4 조정 요소

#### 보너스

| 보너스 유형 | 조건 | 계산 |
|-------------|------|------|
| **조기 완료** | 마감 3일 전 완료 | +{early_completion_bonus}원 |
| **품질 보너스** | 품질 점수 90점 이상 | +{quality_bonus}원 |
| **초과 달성** | 달성률 100% 초과 | +(초과분 × {overachievement_rate}) |
| **첫 미션 완료** | 첫 미션 성공 완료 | +10,000원 (신규 크리에이터 인센티브) |

#### 패널티

| 패널티 유형 | 조건 | 계산 |
|-------------|------|------|
| **지연 제출** | 마감일 초과 | -10% ~ -50% (일수별) |
| **품질 미달** | 품질 점수 50점 미만 | -20% |
| **가이드라인 위반** | 경미한 위반 | -10% ~ -30% |
| **부정 행위** | 봇, 사기 감지 | 전액 차감 + 경고 |

### 4.5 최종 보상 계산

```python
def calculate_final_reward(mission, metrics, quality_score):
    rs = mission.reward_structure

    # 1. 기본 보상 계산
    if rs.reward_type == "fixed":
        base = calculate_fixed(mission, metrics)
    elif rs.reward_type == "performance":
        base = calculate_performance(mission, metrics)
    elif rs.reward_type == "hybrid":
        base = calculate_hybrid(mission, metrics)
    elif rs.reward_type == "tiered":
        base = calculate_tiered(mission, metrics)

    # 2. 보너스 적용
    bonus = 0
    if metrics.completed_before_deadline:
        bonus += rs.early_completion_bonus
    if quality_score >= 90:
        bonus += rs.quality_bonus
    if metrics.achievement_rate > 100:
        overachievement = (metrics.achievement_rate - 100) / 100
        bonus += base * overachievement * rs.overachievement_rate

    # 3. 패널티 적용
    penalty_rate = 0
    if metrics.days_delayed > 0:
        penalty_rate += min(metrics.days_delayed * 0.1, 0.5)
    if quality_score < 50:
        penalty_rate += 0.2

    # 4. 최종 계산
    subtotal = base + bonus
    penalty = subtotal * penalty_rate
    final_reward = max(subtotal - penalty, 0)

    return {
        "base_reward": base,
        "bonus_reward": bonus,
        "penalty_amount": penalty,
        "total_reward": final_reward
    }
```

---

## 5. 정산 프로세스

### 5.1 정산 상태 흐름

```
pending → calculated → reviewed → approved → processing → completed
                        ↓
                     disputed → resolved
                        ↓
                     rejected
```

### 5.2 정산 데이터 모델

```python
class Settlement:
    settlement_id: str
    assignment_id: str
    creator_id: str
    mission_id: str

    # 금액
    base_reward: int
    bonus_reward: int
    penalty_amount: int
    total_reward: int

    # 세금/수수료
    platform_fee: int          # 플랫폼 수수료
    withholding_tax: int       # 원천징수세
    net_amount: int            # 실수령액

    # 상태
    status: SettlementStatus
    calculated_at: datetime
    approved_at: Optional[datetime]
    paid_at: Optional[datetime]

    # 검토
    reviewer_id: Optional[str]
    review_notes: Optional[str]

    # 지급 정보
    payment_method: str        # bank_transfer, paypal 등
    payment_reference: str     # 거래 번호

    # 이의 제기
    dispute_reason: Optional[str]
    dispute_resolved_at: Optional[datetime]
```

### 5.3 정산 주기

| 유형 | 주기 | 조건 |
|------|------|------|
| **일반 정산** | 월 2회 (1일, 15일) | 확정된 정산 건 |
| **즉시 정산** | 완료 후 3일 이내 | 프리미엄 크리에이터 |
| **대량 정산** | 캠페인 종료 후 | 캠페인 단위 일괄 |

### 5.4 정산 검토 기준

| 검토 항목 | 자동 승인 조건 | 수동 검토 조건 |
|----------|----------------|----------------|
| **금액** | < 100만원 | ≥ 100만원 |
| **달성률** | 50-150% | < 50% 또는 > 150% |
| **품질 점수** | ≥ 70 | < 70 |
| **이상 패턴** | 없음 | 급격한 지표 변화 |

---

## 6. 지급 처리

### 6.1 지급 방법

| 방법 | 수수료 | 소요 시간 | 최소 금액 |
|------|--------|-----------|-----------|
| 계좌이체 | 무료 | 1-2 영업일 | 10,000원 |
| PayPal | 3% | 즉시 | $10 |
| 포인트 전환 | 무료 | 즉시 | 1,000원 |

### 6.2 세금 처리

| 항목 | 기준 | 처리 |
|------|------|------|
| **원천징수** | 기타소득 8.8% | 자동 공제 |
| **사업소득** | 사업자 등록된 크리에이터 | 세금계산서 발행 |
| **비거주자** | 해외 크리에이터 | 22% 원천징수 |

### 6.3 지급 확인서

```python
class PaymentConfirmation:
    payment_id: str
    settlement_id: str
    creator_id: str

    gross_amount: int          # 총 보상액
    deductions: List[Deduction] # 공제 항목
    net_amount: int            # 실수령액

    payment_method: str
    payment_date: datetime
    reference_number: str

    # 세금 정보
    tax_type: str
    tax_amount: int
    tax_receipt_issued: bool
```

---

## 7. 데이터 파이프라인

### 7.1 이벤트 수집

```
플랫폼 API / SDK → 이벤트 수집기 → 메시지 큐 → 이벤트 처리기 → 이벤트 저장소
```

### 7.2 집계 파이프라인

```
이벤트 저장소 → 검증기 → 집계기 → 집계 저장소 → 보상 계산기 → 정산 저장소
```

### 7.3 리포팅 파이프라인

```
집계/정산 저장소 → 분석 엔진 → 리포트 생성기 → 대시보드/API
```

---

## 8. API 엔드포인트 설계

### 8.1 성과 조회

```
GET /api/v1/assignments/{assignment_id}/performance
Response:
{
    "assignment_id": "...",
    "metrics": { ... },
    "achievement_rate": 85.5,
    "estimated_reward": 150000
}
```

### 8.2 보상 미리보기

```
GET /api/v1/assignments/{assignment_id}/reward-preview
Response:
{
    "base_reward": 100000,
    "bonus_reward": 20000,
    "penalty_amount": 0,
    "total_reward": 120000,
    "breakdown": { ... }
}
```

### 8.3 정산 목록

```
GET /api/v1/creators/{creator_id}/settlements
Response:
{
    "settlements": [
        {
            "settlement_id": "...",
            "mission_title": "...",
            "total_reward": 150000,
            "net_amount": 136800,
            "status": "completed",
            "paid_at": "..."
        }
    ],
    "summary": {
        "total_earned": 1500000,
        "pending_amount": 200000
    }
}
```

---

## 9. 열거형 정의

```python
class EventType(Enum):
    # 노출
    CONTENT_PUBLISHED = "content_published"
    IMPRESSION = "impression"
    REACH = "reach"
    VIEW_COMPLETE = "view_complete"

    # 참여
    LIKE = "like"
    COMMENT = "comment"
    SHARE = "share"
    SAVE = "save"
    FOLLOW = "follow"

    # 전환
    LINK_CLICK = "link_click"
    PAGE_VIEW = "page_view"
    SIGN_UP = "sign_up"
    APP_INSTALL = "app_install"
    PURCHASE = "purchase"
    LEAD = "lead"

    # 미션
    MISSION_ACCEPTED = "mission_accepted"
    CONTENT_SUBMITTED = "content_submitted"
    CONTENT_APPROVED = "content_approved"
    CONTENT_REJECTED = "content_rejected"
    MISSION_COMPLETED = "mission_completed"

class SettlementStatus(Enum):
    PENDING = "pending"
    CALCULATED = "calculated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PROCESSING = "processing"
    COMPLETED = "completed"
    DISPUTED = "disputed"
    RESOLVED = "resolved"
    REJECTED = "rejected"

class ValidationStatus(Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    FRAUD = "fraud"
    EXCLUDED = "excluded"
```
