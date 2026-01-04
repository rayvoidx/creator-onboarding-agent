---
description: A-Z 자동화 개발 워크플로우 (요구사항 → 배포)
argument-hint: "<requirement-description>"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob, Task
---

# Auto-Dev: Complete Development Workflow

요구사항부터 배포까지 전체 개발 과정을 자동화합니다.

## Workflow Phases

### Phase 1: 요구사항 분석 (Requirements)
1. 사용자 요구사항 파싱
2. 기존 코드베이스 분석
3. 영향받는 파일/모듈 식별
4. 기술적 요구사항 도출

### Phase 2: 설계 (Architecture)
1. 시스템 아키텍처 검토
2. 컴포넌트 설계
3. API 스키마 정의
4. 데이터 모델 설계

### Phase 3: 구현 (Implementation)
1. 백엔드 코드 작성
   - FastAPI 엔드포인트
   - Pydantic 스키마
   - 비즈니스 로직
2. 프론트엔드 코드 작성 (필요시)
   - React 컴포넌트
   - API 연동
3. 테스트 코드 작성
   - Unit tests
   - Integration tests

### Phase 4: 검증 (Verification)
1. Linting & Formatting
   ```bash
   ruff check src/ --fix && ruff format src/
   ```
2. Type Checking
   ```bash
   mypy src/
   ```
3. Unit Tests
   ```bash
   pytest tests/unit/ -v
   ```
4. Integration Tests
   ```bash
   pytest tests/integration/ -v
   ```
5. Coverage Check
   ```bash
   pytest --cov=src --cov-report=term-missing tests/
   ```

### Phase 5: 문서화 (Documentation)
1. API 문서 업데이트
2. README 업데이트 (필요시)
3. CHANGELOG 추가

### Phase 6: 배포 준비 (Deployment)
1. Git commit 생성
2. PR 생성 (gh CLI)
3. CI 파이프라인 확인

## Instructions

$ARGUMENTS를 기반으로 위 Phase들을 순차적으로 실행합니다.

### 자동화 규칙

1. **에러 발생 시**: Ralph Wiggum 방식으로 자동 수정 시도 (최대 10회)
2. **진행 상황 알림**: 각 Phase 완료 시 Slack 알림
3. **블록 시**: 30분 이상 진행 없으면 Slack으로 알림

### 실행 명령

```bash
# Slack 알림 (Phase 시작)
./.claude/hooks/slack-notify.sh "Auto-Dev 시작: $ARGUMENTS" "#dev-notifications" "info"

# 각 Phase 완료 후
./.claude/hooks/slack-notify.sh "Phase N 완료" "#dev-notifications" "success"

# 최종 완료
./.claude/hooks/slack-notify.sh "Auto-Dev 완료: PR 생성됨" "#dev-notifications" "success"
```

## Example Usage

```
/auto-dev "사용자 인증 기능 추가 - JWT 토큰 기반"
/auto-dev "RAG 파이프라인 rerank threshold 0.9로 최적화"
/auto-dev "Creator 온보딩 플로우 개선"
```

## Sub-agents Delegation

복잡한 작업은 서브에이전트에 위임:
- `architect`: 시스템 설계
- `code-reviewer`: 코드 리뷰
- `debugger`: 에러 분석
- `data-analyst`: 메트릭 분석

## Key Files

- `.claude/scripts/auto-verify.sh` - 자동 검증
- `.claude/hooks/slack-notify.sh` - Slack 알림
- `src/` - 소스 코드
- `tests/` - 테스트 코드

## Safety Checks

- `.env` 파일 수정 금지
- `secrets/` 접근 금지
- 위험한 명령 (rm -rf 등) 차단
- 모든 변경사항 git으로 추적
