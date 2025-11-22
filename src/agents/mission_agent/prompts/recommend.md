# Mission Recommendation Prompt

크리에이터에게 적합한 미션을 추천하고 추천 이유를 설명합니다.

---

## 입력 데이터

### 크리에이터 프로필
- **크리에이터 ID**: {creator_id}
- **핸들**: {handle}
- **플랫폼**: {platform}
- **등급**: {grade}
- **팔로워**: {followers:,}명
- **참여율**: {engagement_rate}%
- **카테고리**: {category}
- **리스크**: {risks}
- **완료 미션**: {completed_missions}개
- **평균 품질**: {avg_quality_score}/100
- **현재 진행 미션**: {current_active_missions}개
- **최근 미션 유형**: {recent_mission_types}

### 추천 대상 미션 목록
{mission_list}

### 추천 필터 (선택)
- **미션 유형 필터**: {type_filter}
- **최소 보상**: {min_reward}원
- **최대 난이도**: {max_difficulty}
- **추천 개수**: {limit}개

---

## 추천 프로세스

### 1단계: 자격 필터링
각 미션에 대해 크리에이터의 자격을 확인합니다.

**체크 항목**:
- [ ] 최소 팔로워 충족
- [ ] 최소 참여율 충족
- [ ] 최소 등급 충족
- [ ] 플랫폼 허용 여부
- [ ] 카테고리 허용 여부
- [ ] 리스크 제외 조건

### 2단계: 매칭 스코어 계산
자격을 충족한 미션에 대해 매칭 스코어를 계산합니다.

**스코어 구성**:
| 요소 | 가중치 | 이 크리에이터의 점수 |
|------|--------|----------------------|
| 등급 적합도 | 25% | - |
| 참여율 적합도 | 20% | - |
| 카테고리 적합도 | 20% | - |
| 이력 적합도 | 15% | - |
| 가용성 | 10% | - |
| 다양성 보너스 | 10% | - |

### 3단계: 추천 이유 도출
각 추천 미션에 대해 추천 이유를 생성합니다.

---

## 추천 결과 형식

각 추천 미션에 대해 다음 형식으로 결과를 생성해주세요:

```markdown
## 추천 미션 #{rank}: {mission_title}

### 📊 매칭 스코어: {match_score}/100

### ✅ 추천 이유
1. **{reason_1_title}**: {reason_1_detail}
2. **{reason_2_title}**: {reason_2_detail}
3. **{reason_3_title}**: {reason_3_detail}

### 📈 스코어 상세
| 요소 | 점수 | 설명 |
|------|------|------|
| 등급 적합도 | {grade_score}/25 | {grade_explanation} |
| 참여율 적합도 | {engagement_score}/20 | {engagement_explanation} |
| 카테고리 적합도 | {category_score}/20 | {category_explanation} |
| 이력 적합도 | {history_score}/15 | {history_explanation} |
| 가용성 | {availability_score}/10 | {availability_explanation} |
| 다양성 보너스 | {diversity_score}/10 | {diversity_explanation} |

### 💰 보상 정보
- **보상 유형**: {reward_type}
- **예상 보상**: {expected_reward}원
- **성과 조건**: {performance_condition}

### ⚠️ 주의사항
- {caution_1}
- {caution_2}

### 💡 성공 팁
- {tip_1}
- {tip_2}
```

---

## 전체 추천 요약 형식

```markdown
# {handle}님을 위한 미션 추천

## 📋 추천 요약
- **추천 미션 수**: {recommended_count}개
- **평균 매칭 스코어**: {avg_match_score}
- **총 예상 보상**: {total_expected_reward}원

## 🎯 추천 전략
{recommendation_strategy}

---

[각 미션별 상세 추천]

---

## 📌 종합 의견
{overall_opinion}

## ⏭️ 다음 단계
1. {next_step_1}
2. {next_step_2}
3. {next_step_3}
```

---

## 추천 이유 예시 문구

### 등급 기반
- "S등급 크리에이터로서 고난이도/고보상 미션에 적합합니다"
- "A등급으로 다양한 브랜드 캠페인 참여가 가능합니다"
- "B등급 성장을 위해 중난이도 미션 경험이 도움됩니다"

### 참여율 기반
- "참여율 {engagement_rate}%로 미션 요구사항({min_engagement_rate}%) 대비 {ratio}배 높습니다"
- "높은 참여율로 성과 기반 보상 미션에서 높은 수익이 기대됩니다"

### 카테고리 기반
- "{category} 카테고리 전문성이 이 미션의 타겟 오디언스와 일치합니다"
- "카테고리 적합도가 높아 자연스러운 콘텐츠 제작이 가능합니다"

### 이력 기반
- "{completed_missions}개 미션 완료 경험으로 안정적인 수행이 기대됩니다"
- "평균 품질 점수 {avg_quality_score}점으로 브랜드 기대치 충족이 예상됩니다"

### 다양성 기반
- "최근 {recent_type} 위주 미션을 수행했으므로 {new_type} 미션으로 포트폴리오 다양화"
- "새로운 미션 유형 도전으로 경험 폭을 넓힐 기회입니다"

---

## 주의사항 예시 문구

### 난이도 관련
- "고난이도 미션으로 충분한 준비 시간을 확보하세요"
- "첫 {mission_type} 미션이므로 가이드라인을 꼼꼼히 확인하세요"

### 일정 관련
- "마감까지 {days_left}일 남았습니다. 일정 관리에 유의하세요"
- "현재 {current_active_missions}개 미션 진행 중이므로 일정 조율이 필요합니다"

### 성과 관련
- "성과 기반 보상이므로 목표 달성 전략을 미리 수립하세요"
- "최소 달성률 50% 미만 시 보상이 지급되지 않습니다"

---

## 변수 참조

### 입력 변수
| 변수 | 타입 | 설명 |
|------|------|------|
| `{creator_id}` | string | 크리에이터 ID |
| `{handle}` | string | 핸들 |
| `{platform}` | string | 플랫폼 |
| `{grade}` | string | 등급 |
| `{followers}` | int | 팔로워 수 |
| `{engagement_rate}` | float | 참여율 |
| `{category}` | string | 카테고리 |
| `{risks}` | list | 리스크 태그 |
| `{completed_missions}` | int | 완료 미션 수 |
| `{avg_quality_score}` | float | 평균 품질 점수 |
| `{current_active_missions}` | int | 현재 진행 미션 수 |
| `{recent_mission_types}` | list | 최근 미션 유형 |
| `{mission_list}` | list | 추천 대상 미션 목록 |
| `{type_filter}` | list | 미션 유형 필터 |
| `{min_reward}` | int | 최소 보상 필터 |
| `{max_difficulty}` | string | 최대 난이도 필터 |
| `{limit}` | int | 추천 개수 |

### 출력 변수
| 변수 | 타입 | 설명 |
|------|------|------|
| `{match_score}` | float | 매칭 스코어 |
| `{rank}` | int | 추천 순위 |
| `{recommended_count}` | int | 추천 미션 수 |
| `{avg_match_score}` | float | 평균 매칭 스코어 |
| `{total_expected_reward}` | int | 총 예상 보상 |
| `{recommendation_strategy}` | string | 추천 전략 설명 |
| `{overall_opinion}` | string | 종합 의견 |
