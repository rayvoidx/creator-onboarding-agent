# Creator Evaluation Report Prompt

크리에이터 평가 결과를 사람이 이해하기 쉬운 리포트로 작성해주세요.

---

## 평가 대상 정보

- **플랫폼**: {platform}
- **핸들**: {handle}

## 원본 메트릭

- **팔로워**: {followers:,}명
- **평균 좋아요**: {avg_likes:,}
- **평균 댓글**: {avg_comments:,}
- **30일 게시물**: {posts_30d}개
- **90일 신고 수**: {reports_90d}회
- **브랜드 적합도**: {brand_fit}

## 파생 지표

- **참여율**: {engagement_rate:.2%}
- **일평균 게시물**: {frequency:.2f}

---

## 평가 결과

### 최종 점수: {score} / 100점
### 등급: {grade}
### 결정: {decision}

---

## 점수 구성 분석

| 항목 | 점수 | 최대 | 비율 |
|------|------|------|------|
| 팔로워 영향력 | {score_breakdown[followers]} | 40 | {score_breakdown[followers]/40*100:.0f}% |
| 참여율 | {score_breakdown[engagement]} | 30 | {score_breakdown[engagement]/30*100:.0f}% |
| 활동 빈도 | {score_breakdown[frequency]} | 15 | {score_breakdown[frequency]/15*100:.0f}% |
| 브랜드 적합도 | {score_breakdown[brand_fit]} | 15 | {score_breakdown[brand_fit]/15*100:.0f}% |

---

## 리스크 분석

{% if risks %}
⚠️ **발견된 리스크**:
{% for risk in risks %}
- **{risk}**:
  {% if risk == 'high_reports' %}
  최근 90일 내 신고가 3회 이상으로 플랫폼 정책 위반 가능성이 있습니다. (-15점)
  {% elif risk == 'low_engagement' %}
  참여율이 0.2% 미만으로 팔로워 대비 실질적 영향력이 낮습니다. (-10점)
  {% elif risk == 'low_activity' %}
  최근 30일 게시물이 4개 미만으로 활동이 저조합니다. (-5점)
  {% endif %}
{% endfor %}
{% else %}
✅ 특별한 리스크 요소가 발견되지 않았습니다.
{% endif %}

---

## 추가 태그

{% if tags %}
{% for tag in tags %}
- **{tag}**:
  {% if tag == 'top_candidate' %}
  최우수 후보로 우선 관리 대상입니다.
  {% elif tag == 'needs_awareness_campaign' %}
  인지도 향상을 위한 캠페인이 필요합니다.
  {% elif tag == 'needs_activation' %}
  활동 활성화를 위한 지원이 필요합니다.
  {% endif %}
{% endfor %}
{% else %}
특별한 태그가 부여되지 않았습니다.
{% endif %}

---

## 종합 평가

위 데이터를 바탕으로 다음 내용을 포함하여 종합 평가를 작성해주세요:

1. **핵심 요약** (2-3문장)
   - 이 크리에이터의 가장 큰 강점과 약점
   - 최종 결정({decision})의 근거

2. **강점 분석**
   - 점수가 높은 영역에 대한 구체적 설명
   - 브랜드 파트너십에서 기대할 수 있는 가치

3. **개선 영역**
   - 점수가 낮거나 리스크가 있는 영역
   - 구체적인 개선 방안 제안

4. **활용 방안** (accept/hold인 경우)
   - 어떤 유형의 캠페인에 적합한지
   - 초기 파트너십 시 권장 사항

5. **재평가 기준** (reject/hold인 경우)
   - 재평가를 위해 필요한 조건
   - 개선 목표 수치

---

## 출력 형식

리포트는 다음 형식으로 작성해주세요:

```
## 크리에이터 평가 리포트

### 📊 핵심 요약
[2-3문장의 핵심 요약]

### ✅ 강점
- [강점 1]
- [강점 2]

### ⚠️ 개선 영역
- [개선점 1]
- [개선점 2]

### 💡 권장 사항
[활용 방안 또는 재평가 기준]

### 📈 다음 단계
[구체적인 액션 아이템]
```

---

## 변수 참조

### 기본 정보
- `{platform}`: 플랫폼명
- `{handle}`: 크리에이터 핸들

### 메트릭
- `{followers}`: 팔로워 수
- `{avg_likes}`: 평균 좋아요
- `{avg_comments}`: 평균 댓글
- `{posts_30d}`: 30일 게시물
- `{reports_90d}`: 90일 신고 수
- `{brand_fit}`: 브랜드 적합도 (0.0-1.0)

### 파생 지표
- `{engagement_rate}`: 참여율 (소수점 형태, 예: 0.032 = 3.2%)
- `{frequency}`: 일평균 게시물 수

### 평가 결과
- `{score}`: 최종 점수 (0-100)
- `{grade}`: 등급 (S/A/B/C)
- `{decision}`: 결정 (accept/hold/reject)
- `{risks}`: 리스크 태그 리스트 (예: ['high_reports', 'low_engagement'])
- `{tags}`: 추가 태그 리스트 (예: ['top_candidate'])
- `{score_breakdown}`: 점수 구성 딕셔너리
  - `{score_breakdown[followers]}`: 팔로워 점수
  - `{score_breakdown[engagement]}`: 참여율 점수
  - `{score_breakdown[frequency]}`: 활동 빈도 점수
  - `{score_breakdown[brand_fit]}`: 브랜드 적합도 점수
