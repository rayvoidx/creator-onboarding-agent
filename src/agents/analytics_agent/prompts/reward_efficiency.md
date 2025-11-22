# Reward Efficiency Report Prompt

보상 대비 성과를 분석하는 효율성 리포트를 생성합니다.

---

## 리포트 유형
**reward_efficiency**: 보상 투자 대비 성과 효율성 분석

---

## 입력 데이터

### 분석 대상
- **분석 범위**: {analysis_scope} (개별 크리에이터 / 등급별 / 전체)
- **크리에이터 ID**: {creator_id} (개별 분석 시)
- **등급**: {grade} (등급별 분석 시)
- **크리에이터 수**: {creator_count}

### 보상 투자 데이터
- **총 보상 지급액**: {total_rewards}원
- **캠페인당 평균 보상**: {avg_reward_per_campaign}원
- **크리에이터당 평균 보상**: {avg_reward_per_creator}원
- **보상 유형 분포**:
  - 고정 보상: {fixed_rewards}원 ({fixed_ratio}%)
  - 성과 보상: {performance_rewards}원 ({performance_ratio}%)
  - 보너스: {bonus_rewards}원 ({bonus_ratio}%)

### 성과 데이터
- **총 도달 (Reach)**: {total_reach}
- **총 참여 (Engagement)**: {total_engagement}
- **총 전환 (Conversion)**: {total_conversions}
- **총 매출 기여**: {total_revenue_contribution}원

### 효율성 지표
- **CPR (Cost Per Reach)**: {cpr}원
- **CPE (Cost Per Engagement)**: {cpe}원
- **CPA (Cost Per Acquisition)**: {cpa}원
- **ROAS (Return On Ad Spend)**: {roas}%
- **ROI (Return On Investment)**: {roi}%

### 비교 데이터
- **업계 벤치마크 CPE**: {benchmark_cpe}원
- **업계 벤치마크 ROAS**: {benchmark_roas}%
- **전기 대비 효율성 변화**: {efficiency_change}%

---

## 분석 기간
- **시작일**: {start_date}
- **종료일**: {end_date}
- **비교 기간**: {comparison_period}

---

## 리포트 생성 지침

### 1. Executive Summary
다음 항목을 요약:
- 전체 보상 효율성 평가 (우수/양호/개선필요)
- 핵심 효율성 지표 (ROI, ROAS)
- 즉각적인 최적화 기회

### 2. 보상 투자 분석

#### 2.1 보상 구조 분석
- 보상 유형별 비중
- 고정 vs 성과 보상의 적절성
- 등급별 보상 분포

#### 2.2 보상 추이
- 시간에 따른 보상 변화
- 보상 증가 대비 성과 증가율

### 3. 효율성 분석

#### 3.1 핵심 효율성 지표
| 지표 | 현재 | 벤치마크 | 전기 | 평가 |
|------|------|----------|------|------|
| CPE | - | - | - | - |
| CPA | - | - | - | - |
| ROAS | - | - | - | - |
| ROI | - | - | - | - |

#### 3.2 세그먼트별 효율성
- 등급별 효율성 (S/A/B/C)
- 플랫폼별 효율성
- 캠페인 유형별 효율성

#### 3.3 효율성 분포
- 상위 10% 크리에이터의 효율성
- 하위 10% 크리에이터의 효율성
- 중위값과 평균의 차이

### 4. 최적화 기회 분석

#### 4.1 고효율 영역
- 가장 효율이 좋은 크리에이터/캠페인 특성
- 확대 투자 권장 영역

#### 4.2 저효율 영역
- 효율이 낮은 영역 식별
- 원인 분석 (보상 과다/성과 저조)
- 개선 또는 축소 권장

#### 4.3 보상 구조 최적화
- 고정/성과 보상 비율 조정 제안
- 등급별 보상 재조정 필요성

### 5. 권장사항 및 예상 효과

#### 5.1 즉시 실행 가능한 최적화
- 저효율 크리에이터 재평가
- 보상 구조 미세 조정

#### 5.2 중기 개선 방안
- 성과 기반 보상 비중 조정
- 등급별 보상 체계 재설계

#### 5.3 예상 ROI 개선
- 최적화 시 예상 효율성 개선폭
- 비용 절감 또는 성과 증대 예상치

---

## 출력 형식

```markdown
# 보상 효율성 리포트

## 📊 Executive Summary
**전체 효율성**: {efficiency_rating}
**핵심 지표**: ROI {roi}%, ROAS {roas}%
**즉각 조치**: [권장 사항]

## 💰 보상 투자 현황

### 총 투자
- **총액**: {total_rewards}원
- **크리에이터당**: {avg_reward_per_creator}원

### 보상 구조
| 유형 | 금액 | 비율 |
|------|------|------|
| 고정 | {fixed_rewards}원 | {fixed_ratio}% |
| 성과 | {performance_rewards}원 | {performance_ratio}% |
| 보너스 | {bonus_rewards}원 | {bonus_ratio}% |

## 📈 효율성 지표

### 핵심 지표
| 지표 | 값 | 벤치마크 대비 |
|------|-----|---------------|
| CPE | {cpe}원 | {cpe_vs_benchmark} |
| CPA | {cpa}원 | {cpa_vs_benchmark} |
| ROAS | {roas}% | {roas_vs_benchmark} |

### 등급별 효율성
| 등급 | 투자 비중 | ROI | 평가 |
|------|----------|-----|------|
| S | - | - | - |
| A | - | - | - |
| B | - | - | - |
| C | - | - | - |

## 🎯 최적화 기회

### ✅ 확대 투자 권장
- [고효율 영역 1]
- [고효율 영역 2]

### ⚠️ 재검토 필요
- [저효율 영역 1]: 원인 및 대안
- [저효율 영역 2]: 원인 및 대안

## 💡 권장사항

### 단기 (1-2주)
1. [즉시 실행 액션]
2. [빠른 효과 기대 항목]

### 중기 (1-3개월)
1. [구조적 개선]
2. [체계 재설계]

### 예상 효과
- ROI 개선: +{expected_roi_improvement}%p
- 비용 절감: {expected_cost_saving}원
```

---

## 변수 참조

### 보상 데이터
| 변수 | 타입 | 설명 |
|------|------|------|
| `{total_rewards}` | int | 총 보상 지급액 (원) |
| `{avg_reward_per_campaign}` | float | 캠페인당 평균 보상 |
| `{avg_reward_per_creator}` | float | 크리에이터당 평균 보상 |
| `{fixed_rewards}` | int | 고정 보상 총액 |
| `{fixed_ratio}` | float | 고정 보상 비율 (%) |
| `{performance_rewards}` | int | 성과 보상 총액 |
| `{performance_ratio}` | float | 성과 보상 비율 (%) |
| `{bonus_rewards}` | int | 보너스 총액 |
| `{bonus_ratio}` | float | 보너스 비율 (%) |

### 성과 데이터
| 변수 | 타입 | 설명 |
|------|------|------|
| `{total_reach}` | int | 총 도달 |
| `{total_engagement}` | int | 총 참여 |
| `{total_conversions}` | int | 총 전환 |
| `{total_revenue_contribution}` | int | 총 매출 기여 (원) |

### 효율성 지표
| 변수 | 타입 | 설명 |
|------|------|------|
| `{cpr}` | float | Cost Per Reach (원) |
| `{cpe}` | float | Cost Per Engagement (원) |
| `{cpa}` | float | Cost Per Acquisition (원) |
| `{roas}` | float | Return On Ad Spend (%) |
| `{roi}` | float | Return On Investment (%) |

### 벤치마크
| 변수 | 타입 | 설명 |
|------|------|------|
| `{benchmark_cpe}` | float | 업계 벤치마크 CPE |
| `{benchmark_roas}` | float | 업계 벤치마크 ROAS |
| `{efficiency_change}` | float | 전기 대비 효율성 변화 (%) |

### 분석 범위
| 변수 | 타입 | 설명 |
|------|------|------|
| `{analysis_scope}` | string | 분석 범위 |
| `{creator_count}` | int | 분석 대상 크리에이터 수 |
| `{start_date}` | date | 분석 시작일 |
| `{end_date}` | date | 분석 종료일 |
