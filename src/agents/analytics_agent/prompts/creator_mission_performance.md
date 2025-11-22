# Creator Mission Performance Report Prompt

온보딩 점수와 미션 성과를 비교 분석하는 리포트를 생성합니다.

---

## 리포트 유형
**creator_mission_performance**: 온보딩 평가 vs 실제 미션 성과 비교

---

## 입력 데이터

### 온보딩 평가 정보
- **크리에이터 ID**: {creator_id}
- **핸들**: {handle}
- **온보딩 점수**: {onboarding_score}/100
- **예측 등급**: {predicted_grade}
- **평가 일자**: {evaluation_date}
- **평가 시 메트릭**:
  - 팔로워: {eval_followers}
  - 참여율: {eval_engagement_rate}%
  - 활동 빈도: {eval_frequency}
  - 브랜드 적합도: {eval_brand_fit}

### 실제 미션 성과
- **참여 미션 수**: {mission_count}
- **완료 미션 수**: {completed_missions}
- **미션 완수율**: {mission_completion_rate}%
- **평균 미션 품질 점수**: {avg_quality_score}/100
- **평균 응답 시간**: {avg_response_time}시간

### 미션별 성과 상세
- **미션 목록**: {mission_list}
  - 미션 ID: {mission_id}
  - 미션 유형: {mission_type}
  - 목표 도달: {target_reach}
  - 실제 도달: {actual_reach}
  - 달성률: {achievement_rate}%
  - 참여율: {mission_engagement_rate}%
  - 품질 점수: {quality_score}/100

### 기대 vs 실제 비교
- **예상 성과 범위**: {expected_performance_range}
- **실제 평균 성과**: {actual_avg_performance}
- **괴리도**: {gap_percentage}%

---

## 분석 기간
- **온보딩 후 경과일**: {days_since_onboarding}
- **분석 기간**: {analysis_period}

---

## 리포트 생성 지침

### 1. Executive Summary
다음 항목을 요약:
- 온보딩 평가와 실제 성과의 일치도
- 예측 정확도 평가 (과대평가/적절/과소평가)
- 주요 발견사항

### 2. 온보딩 평가 vs 실제 성과 비교

#### 2.1 점수 비교 테이블
| 항목 | 온보딩 시 | 현재 | 변화 | 평가 |
|------|----------|------|------|------|
| 팔로워 | - | - | - | ✅/❌ |
| 참여율 | - | - | - | ✅/❌ |
| 활동성 | - | - | - | ✅/❌ |

#### 2.2 예측 정확도 분석
- 온보딩 점수가 실제 성과를 얼마나 잘 예측했는지
- 과대평가된 영역
- 과소평가된 영역

### 3. 미션 성과 상세 분석

#### 3.1 미션 유형별 성과
- 어떤 유형의 미션에서 강점을 보이는지
- 어떤 유형에서 약점을 보이는지

#### 3.2 시간 경과에 따른 성과 변화
- 첫 미션 vs 최근 미션 성과 비교
- 학습 곡선 분석

#### 3.3 품질 vs 양적 성과
- 품질 점수와 도달/참여의 상관관계
- 최적의 밸런스 지점

### 4. 등급 재평가 권장

#### 4.1 현재 등급의 적절성
- 실제 성과 기반 권장 등급
- 등급 조정 필요 여부

#### 4.2 평가 모델 피드백
- 온보딩 평가 모델의 개선점
- 가중치 조정 제안

### 5. 인사이트 및 권장사항

#### 5.1 크리에이터 관리 방향
- 어떤 미션에 우선 배정할지
- 코칭/지원이 필요한 영역

#### 5.2 평가 모델 개선 제안
- 이 케이스에서 배울 수 있는 점
- 유사 프로필에 대한 예측 개선

---

## 출력 형식

```markdown
# 온보딩 vs 미션 성과 분석: {handle}

## 📊 핵심 요약
**예측 정확도**: {accuracy_assessment}
**등급 적절성**: {grade_appropriateness}

## 📈 비교 분석

### 온보딩 평가 시점
- 점수: {onboarding_score}/100
- 예측 등급: {predicted_grade}

### 실제 미션 성과
- 완수율: {mission_completion_rate}%
- 평균 품질: {avg_quality_score}/100
- 평균 달성률: {avg_achievement_rate}%

### 괴리도 분석
| 지표 | 예상 | 실제 | 괴리 |
|------|------|------|------|
| 참여율 | - | - | - |
| 품질 | - | - | - |

## 💡 발견사항

### ✅ 예측이 정확했던 영역
- [영역 1]
- [영역 2]

### ⚠️ 괴리가 컸던 영역
- [영역 1]: 원인 분석
- [영역 2]: 원인 분석

## 🎯 권장사항

### 크리에이터 관리
1. [권장 미션 유형]
2. [지원 필요 영역]

### 평가 모델 개선
1. [가중치 조정 제안]
2. [추가 지표 고려]

## 📅 등급 재평가
- **현재 등급**: {predicted_grade}
- **권장 등급**: {recommended_grade}
- **조정 근거**: [설명]
```

---

## 변수 참조

### 온보딩 평가
| 변수 | 타입 | 설명 |
|------|------|------|
| `{onboarding_score}` | float | 온보딩 평가 점수 (0-100) |
| `{predicted_grade}` | string | 예측 등급 (S/A/B/C) |
| `{evaluation_date}` | date | 평가 일자 |
| `{eval_followers}` | int | 평가 시 팔로워 |
| `{eval_engagement_rate}` | float | 평가 시 참여율 |
| `{eval_frequency}` | float | 평가 시 활동 빈도 |
| `{eval_brand_fit}` | float | 평가 시 브랜드 적합도 |

### 미션 성과
| 변수 | 타입 | 설명 |
|------|------|------|
| `{mission_count}` | int | 참여 미션 수 |
| `{completed_missions}` | int | 완료 미션 수 |
| `{mission_completion_rate}` | float | 미션 완수율 (%) |
| `{avg_quality_score}` | float | 평균 품질 점수 (0-100) |
| `{avg_response_time}` | float | 평균 응답 시간 (시간) |

### 미션 상세
| 변수 | 타입 | 설명 |
|------|------|------|
| `{mission_list}` | list | 미션 상세 목록 |
| `{mission_id}` | string | 미션 ID |
| `{mission_type}` | string | 미션 유형 |
| `{target_reach}` | int | 목표 도달 |
| `{actual_reach}` | int | 실제 도달 |
| `{achievement_rate}` | float | 달성률 (%) |

### 비교 분석
| 변수 | 타입 | 설명 |
|------|------|------|
| `{expected_performance_range}` | string | 예상 성과 범위 |
| `{actual_avg_performance}` | float | 실제 평균 성과 |
| `{gap_percentage}` | float | 괴리도 (%) |
| `{days_since_onboarding}` | int | 온보딩 후 경과일 |
