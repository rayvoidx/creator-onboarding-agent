---
description: Creator 추천 A/B 테스트 관리
argument-hint: "[action] [experiment-id]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# A/B Test Agent

A/B 테스트 실험을 설계하고 분석합니다.

## Instructions

1. 실험 설계:
   - Variant 정의 (control, treatment)
   - Traffic split 설정
   - 성공 메트릭 정의

2. 결과 분석:
   - 통계적 유의성 검증 (p-value)
   - Confidence interval 계산
   - Bayesian 분석

3. 승자 롤아웃

## Arguments
- `$ARGUMENTS` - 액션 및 실험 ID

## Experiment Structure
```python
{
    "experiment_id": "rec_algo_v2",
    "variants": ["control", "treatment"],
    "traffic_split": [0.5, 0.5],
    "metrics": ["click_rate", "conversion"]
}
```

## Key Files
- `src/services/ab_testing/service.py`
- `src/api/routes/ab_testing_routes.py`
