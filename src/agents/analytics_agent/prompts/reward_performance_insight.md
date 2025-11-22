# Reward & Performance Insight Report Prompt

보상/성과/효율성에 대한 인사이트 리포트를 생성합니다.

---

## 리포트 유형
**reward_performance_insight**: 보상-성과 관계 분석 및 인사이트 도출

---

## 질의 예시

### 효율성 분석
- "이번 달 보상 효율성은 어떤가요?"
- "ROI가 가장 높은 크리에이터는 누구인가요?"
- "CPE(참여당 비용)가 업계 벤치마크 대비 어떤가요?"

### 성과 분석
- "성과 기반 보상과 고정 보상 중 어떤 것이 더 효과적인가요?"
- "등급별 성과 차이가 얼마나 되나요?"
- "미션 유형별 달성률은 어떤가요?"

### 최적화 제안
- "보상 구조를 어떻게 개선해야 할까요?"
- "저효율 영역은 어디인가요?"
- "투자를 확대해야 할 세그먼트는?"

### 트렌드 분석
- "지난 분기 대비 효율성이 어떻게 변했나요?"
- "시간에 따른 ROI 추이는?"
- "계절적 패턴이 있나요?"

---

## 입력 데이터

### 분석 범위
- **분석 기간**: {start_date} ~ {end_date}
- **비교 기간**: {comparison_period}
- **분석 대상**: {analysis_scope} (전체/등급별/캠페인별/크리에이터별)

### 보상 데이터
- **총 지급 보상**: {total_rewards}원
- **크리에이터 수**: {creator_count}명
- **미션 수**: {mission_count}개
- **보상 유형별 비중**: {reward_type_distribution}

### 성과 데이터
- **총 도달**: {total_reach}
- **총 참여**: {total_engagement}
- **총 전환**: {total_conversions}
- **총 매출 기여**: {total_revenue}원

### 효율성 지표
- **CPR**: {cpr}원
- **CPE**: {cpe}원
- **CPA**: {cpa}원
- **ROAS**: {roas}%
- **ROI**: {roi}%

### 세그먼트별 데이터
- **등급별 성과**: {grade_performance}
- **미션 유형별 성과**: {mission_type_performance}
- **플랫폼별 성과**: {platform_performance}

---

## 리포트 구조

### 1. Executive Summary (경영진 요약)

#### 핵심 발견사항
3-5개 불릿 포인트로 요약:
- 가장 중요한 효율성 지표와 트렌드
- 즉각적인 주의가 필요한 영역
- 가장 큰 기회 영역

#### 핵심 숫자
| 지표 | 현재 | 전기 대비 | 평가 |
|------|------|-----------|------|
| ROI | {roi}% | {roi_change}%p | ✅/⚠️/❌ |
| ROAS | {roas}% | {roas_change}%p | ✅/⚠️/❌ |
| CPE | {cpe}원 | {cpe_change}% | ✅/⚠️/❌ |

### 2. 효율성 심층 분석

#### 2.1 전체 효율성 현황
- 벤치마크 대비 위치
- 효율성 트렌드 (개선/악화)
- 주요 영향 요인

#### 2.2 세그먼트별 효율성

**등급별 분석**
| 등급 | 투자 비중 | ROI | CPE | 평가 |
|------|----------|-----|-----|------|
| S | {s_investment}% | {s_roi}% | {s_cpe}원 | {s_eval} |
| A | {a_investment}% | {a_roi}% | {a_cpe}원 | {a_eval} |
| B | {b_investment}% | {b_roi}% | {b_cpe}원 | {b_eval} |
| C | {c_investment}% | {c_roi}% | {c_cpe}원 | {c_eval} |

**미션 유형별 분석**
| 유형 | 미션 수 | 평균 보상 | 달성률 | ROI |
|------|---------|-----------|--------|-----|
| 콘텐츠 제작 | - | - | - | - |
| 참여형 | - | - | - | - |
| 트래픽 유도 | - | - | - | - |
| 브랜딩 | - | - | - | - |

#### 2.3 보상 구조별 효과

| 보상 유형 | 미션 수 | 평균 달성률 | 크리에이터 만족도 |
|-----------|---------|-------------|-------------------|
| 고정 | - | - | - |
| 성과 기반 | - | - | - |
| 하이브리드 | - | - | - |
| 단계별 | - | - | - |

### 3. 인사이트 & 패턴

#### 3.1 성공 패턴
- 고효율을 달성한 케이스의 공통점
- 초과 달성 크리에이터의 특성
- 최적의 보상 구조 조합

#### 3.2 개선 필요 영역
- 저효율 세그먼트 식별
- 원인 분석 (보상 과다/성과 저조)
- 이탈 위험 크리에이터

#### 3.3 기회 영역
- 확대 투자가 유망한 세그먼트
- 새로운 보상 모델 테스트 기회
- 미개척 시장/카테고리

### 4. 최적화 권장사항

#### 4.1 즉시 실행 (1-2주)
우선순위 높은 빠른 개선:
1. {immediate_action_1}
   - 예상 효과: {effect_1}
2. {immediate_action_2}
   - 예상 효과: {effect_2}

#### 4.2 중기 개선 (1-3개월)
구조적 개선:
1. {medium_term_action_1}
   - 실행 방안: {implementation_1}
   - 예상 효과: {effect_3}
2. {medium_term_action_2}
   - 실행 방안: {implementation_2}
   - 예상 효과: {effect_4}

#### 4.3 장기 전략 (3개월+)
1. {long_term_strategy_1}
2. {long_term_strategy_2}

### 5. 예상 효과 및 목표

#### ROI 개선 예상
| 시나리오 | ROI 개선 | 비용 절감 | 성과 증대 |
|----------|----------|-----------|-----------|
| 보수적 | +{conservative_roi}%p | {conservative_saving}원 | +{conservative_perf}% |
| 기본 | +{base_roi}%p | {base_saving}원 | +{base_perf}% |
| 낙관적 | +{optimistic_roi}%p | {optimistic_saving}원 | +{optimistic_perf}% |

#### 다음 분기 목표
- ROI: {target_roi}% (현재 대비 +{roi_improvement}%p)
- CPE: {target_cpe}원 (현재 대비 {cpe_improvement}%)
- 달성률: {target_achievement}%

---

## 출력 형식

```markdown
# 보상-성과 인사이트 리포트
**분석 기간**: {start_date} ~ {end_date}

## 📊 Executive Summary

### 핵심 발견사항
- {key_finding_1}
- {key_finding_2}
- {key_finding_3}

### 핵심 지표
| 지표 | 값 | 변화 | 상태 |
|------|-----|------|------|
| ROI | {roi}% | {roi_change} | {roi_status} |
| ROAS | {roas}% | {roas_change} | {roas_status} |
| CPE | {cpe}원 | {cpe_change} | {cpe_status} |

---

## 📈 효율성 분석

### 등급별 효율성
[등급별 분석 표]

### 미션 유형별 효율성
[미션 유형별 분석 표]

### 보상 구조별 효과
[보상 구조 분석]

---

## 💡 인사이트

### ✅ 성공 패턴
- {success_pattern_1}
- {success_pattern_2}

### ⚠️ 개선 필요
- {improvement_area_1}
- {improvement_area_2}

### 🎯 기회 영역
- {opportunity_1}
- {opportunity_2}

---

## 🚀 권장사항

### 즉시 실행
1. {action_1}
2. {action_2}

### 중기 개선
1. {medium_action_1}
2. {medium_action_2}

### 예상 효과
- ROI 개선: +{roi_improvement}%p
- 비용 절감: {cost_saving}원

---

## 📅 다음 단계
1. {next_step_1}
2. {next_step_2}
3. {next_step_3}
```

---

## 변수 참조

### 기간/범위
| 변수 | 타입 | 설명 |
|------|------|------|
| `{start_date}` | date | 분석 시작일 |
| `{end_date}` | date | 분석 종료일 |
| `{comparison_period}` | string | 비교 기간 |
| `{analysis_scope}` | string | 분석 범위 |

### 보상 데이터
| 변수 | 타입 | 설명 |
|------|------|------|
| `{total_rewards}` | int | 총 보상 지급액 |
| `{creator_count}` | int | 크리에이터 수 |
| `{mission_count}` | int | 미션 수 |
| `{reward_type_distribution}` | dict | 보상 유형별 분포 |

### 성과 데이터
| 변수 | 타입 | 설명 |
|------|------|------|
| `{total_reach}` | int | 총 도달 |
| `{total_engagement}` | int | 총 참여 |
| `{total_conversions}` | int | 총 전환 |
| `{total_revenue}` | int | 총 매출 기여 |

### 효율성 지표
| 변수 | 타입 | 설명 |
|------|------|------|
| `{cpr}` | float | Cost Per Reach |
| `{cpe}` | float | Cost Per Engagement |
| `{cpa}` | float | Cost Per Acquisition |
| `{roas}` | float | Return On Ad Spend |
| `{roi}` | float | Return On Investment |

### 세그먼트 데이터
| 변수 | 타입 | 설명 |
|------|------|------|
| `{grade_performance}` | dict | 등급별 성과 |
| `{mission_type_performance}` | dict | 미션 유형별 성과 |
| `{platform_performance}` | dict | 플랫폼별 ���과 |

### 변화율
| 변수 | 타입 | 설명 |
|------|------|------|
| `{roi_change}` | float | ROI 변화 (%p) |
| `{roas_change}` | float | ROAS 변화 (%p) |
| `{cpe_change}` | float | CPE 변화 (%) |

### 권장사항/예상
| 변수 | 타입 | 설명 |
|------|------|------|
| `{immediate_action_1}` | string | 즉시 실행 액션 |
| `{roi_improvement}` | float | ROI 개선 예상치 |
| `{cost_saving}` | int | 비용 절감 예상치 |
