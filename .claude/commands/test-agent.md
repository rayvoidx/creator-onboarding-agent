---
description: pytest 커버리지 95% 달성 및 E2E 테스트
argument-hint: "[target] [coverage-goal]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Test Agent

테스트 커버리지를 분석하고 향상시킵니다.

## Instructions

1. 현재 커버리지 확인:
   ```bash
   pytest --cov=src --cov-report=term-missing tests/
   ```

2. 커버리지가 낮은 모듈 식별

3. 누락된 테스트 케이스 작성:
   - Unit tests: `tests/unit/`
   - Integration tests: `tests/integration/`
   - E2E tests: `tests/e2e/`

4. 목표: 90% → 95% 커버리지

## Arguments
- `$ARGUMENTS` - 타겟 모듈 또는 커버리지 목표

## Key Files
- `tests/conftest.py`
- `tests/unit/`
- `tests/integration/`
- `.github/workflows/ci.yml`
