# Creator Performance Summary Report Prompt

크리에이터별 기본 성과 요약 리포트를 생성합니다.

---

## 리포트 유형
**creator_performance_summary**: 크리에이터별 기본 성과 요약

---

## 입력 데이터

### 크리에이터 기본 정보
- **크리에이터 ID**: {creator_id}
- **핸들**: {handle}
- **플랫폼**: {platform}
- **등급**: {grade}
- **온보딩 일자**: {onboarding_date}

### 성과 메트릭
- **팔로워 수**: {followers}
- **팔로워 변화**: {follower_change} ({follower_change_rate}%)
- **평균 참여율**: {engagement_rate}%
- **총 게시물**: {total_posts}
- **활동 기간**: {active_days}일

### 캠페인 성과
- **참여 캠페인 수**: {campaign_count}
- **완료 캠페인 수**: {completed_campaigns}
- **평균 ROI**: {avg_roi}%
- **총 도달**: {total_reach}
- **총 참여**: {total_engagement}

### 보상 정보
- **총 지급 보상**: {total_rewards}원
- **평균 캠페인당 보상**: {avg_reward_per_campaign}원
- **보상 대비 성과율**: {reward_efficiency}%

---

## 분석 기간
- **시작일**: {start_date}
- **종료일**: {end_date}
- **비교 기간**: {comparison_period}

---

## 리포트 생성 지침

### 1. Executive Summary (경영진 요약)
다음 항목을 1-2문장으로 요약:
- 크리에이터의 전반적인 성과 평가
- 핵심 강점과 개선 영역
- 추천 액션 (계속 투자 / 모니터링 / 재검토)

### 2. 성과 지표 분석

#### 2.1 영향력 지표
- 팔로워 성장 추이
- 도달률 및 노출 효과
- 팔로워 품질 (참여율 기반)

#### 2.2 참여도 지표
- 평균 참여율 vs 플랫폼 벤치마크
- 참여 유형 분석 (좋아요, 댓글, 공유)
- 참여 추세 (증가/감소/안정)

#### 2.3 캠페인 성과
- 캠페인 완수율
- 평균 ROI 및 효율성
- 최고/최저 성과 캠페인

### 3. 비교 분석

#### 3.1 전기 대비
- 주요 지표 증감률
- 개선된 영역
- 하락한 영역

#### 3.2 동급 대비
- 동일 등급 크리에이터 평균 대비 성과
- 상위/하위 백분위

### 4. 인사이트 및 권장사항

#### 4.1 강점 활용 방안
- 어떤 유형의 캠페인에 적합한지
- 최적의 콘텐츠 형식

#### 4.2 개선 권장사항
- 구체적인 개선 액션
- 예상 효과

#### 4.3 등급 전망
- 현재 등급 유지/승급/하락 예상
- 승급 조건 및 목표

---

## 출력 형식

```markdown
# 크리에이터 성과 리포트: {handle}

## 📊 Executive Summary
[2-3문장 요약]

## 📈 핵심 지표
| 지표 | 현재 | 전기 | 변화 |
|------|------|------|------|
| 팔로워 | {followers} | - | {follower_change_rate}% |
| 참여율 | {engagement_rate}% | - | - |
| 캠페인 ROI | {avg_roi}% | - | - |

## 💪 강점
- [강점 1]
- [강점 2]

## ⚠️ 개선 영역
- [개선점 1]
- [개선점 2]

## 💡 권장사항
1. [단기 액션]
2. [중기 액션]
3. [장기 목표]

## 📅 다음 단계
- [구체적 액션 아이템]
```

---

## 변수 참조

### 기본 정보
| 변수 | 타입 | 설명 |
|------|------|------|
| `{creator_id}` | string | 크리에이터 고유 ID |
| `{handle}` | string | 핸들/사용자명 |
| `{platform}` | string | 플랫폼 (tiktok, instagram 등) |
| `{grade}` | string | 등급 (S/A/B/C) |
| `{onboarding_date}` | date | 온보딩 일자 |

### 성과 메트릭
| 변수 | 타입 | 설명 |
|------|------|------|
| `{followers}` | int | 현재 팔로워 수 |
| `{follower_change}` | int | 팔로워 증감 |
| `{follower_change_rate}` | float | 팔로워 증감률 (%) |
| `{engagement_rate}` | float | 평균 참여율 (%) |
| `{total_posts}` | int | 총 게시물 수 |
| `{active_days}` | int | 활동 일수 |

### 캠페인 성과
| 변수 | 타입 | 설명 |
|------|------|------|
| `{campaign_count}` | int | 참여 캠페인 수 |
| `{completed_campaigns}` | int | 완료 캠페인 수 |
| `{avg_roi}` | float | 평균 ROI (%) |
| `{total_reach}` | int | 총 도달 |
| `{total_engagement}` | int | 총 참여 |

### 보상 정보
| 변수 | 타입 | 설명 |
|------|------|------|
| `{total_rewards}` | int | 총 지급 보상 (원) |
| `{avg_reward_per_campaign}` | float | 캠페인당 평균 보상 |
| `{reward_efficiency}` | float | 보상 대비 성과율 (%) |

### 기간
| 변수 | 타입 | 설명 |
|------|------|------|
| `{start_date}` | date | 분석 시작일 |
| `{end_date}` | date | 분석 종료일 |
| `{comparison_period}` | string | 비교 기간 (전주/전월/전분기) |
