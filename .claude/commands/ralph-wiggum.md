---
description: Ralph Wiggum 자동 반복 검증 실행
argument-hint: "[start|stop|status|verify]"
allowed-tools: Bash, Read, Edit, Write, Grep, Glob
---

# Ralph Wiggum Auto-Verification

"I'm helping!" - Claude가 자체적으로 테스트를 반복 실행하고 모든 검증이 통과할 때까지 수정합니다.

## Instructions

### 명령어

1. **검증 시작** (백그라운드):
   ```bash
   ./.claude/scripts/ralph-wiggum.sh start
   ```

2. **검증 중지**:
   ```bash
   ./.claude/scripts/ralph-wiggum.sh stop
   ```

3. **상태 확인**:
   ```bash
   ./.claude/scripts/ralph-wiggum.sh status
   ```

4. **즉시 검증** (포그라운드):
   ```bash
   ./.claude/scripts/auto-verify.sh
   ```

### 검증 단계

1. **Linting**: ruff (Python), ESLint (JS/TS)
2. **Type Check**: mypy (Python), tsc (TypeScript)
3. **Tests**: pytest, npm test
4. **Build**: 프론트엔드 빌드 검증

### 동작 방식

- 최대 10회 반복 (MAX_ITERATIONS 환경변수로 조정)
- 각 반복마다 모든 검증 실행
- 실패 시 5초 대기 후 재시도
- Slack으로 진행 상황 알림
- 로그: `.claude/hooks/verification.log`

## Arguments

- `$ARGUMENTS`:
  - `start`: 백그라운드 검증 시작
  - `stop`: 검증 중지
  - `status`: 현재 상태 확인
  - `verify`: 즉시 검증 (포그라운드)

## Example Usage

```
/ralph-wiggum start
/ralph-wiggum status
/ralph-wiggum stop
```

## Configuration

환경변수로 동작 조정:
- `MAX_ITERATIONS=10`: 최대 반복 횟수
- `PROJECT_ROOT=$(pwd)`: 프로젝트 루트

## Key Files

- `.claude/scripts/auto-verify.sh` - 검증 로직
- `.claude/scripts/ralph-wiggum.sh` - 래퍼 스크립트
- `.claude/hooks/verification.log` - 검증 로그
- `.claude/hooks/ralph.pid` - PID 파일
