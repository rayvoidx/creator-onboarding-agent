---
description: tmux/Claude Squad 멀티 세션 관리
argument-hint: "[start|list|setup|stop]"
allowed-tools: Bash, Read
---

# Multi-Session Manager

여러 Claude Code 세션을 병렬로 실행하여 개발 속도를 높입니다.

## Instructions

### 기본 사용법 (tmux)

```bash
# 병렬 개발 환경 설정 (3개 세션 + worktrees)
./.claude/scripts/multi-session.sh setup

# 개별 세션 시작
./.claude/scripts/multi-session.sh start feature "Implement auth"
./.claude/scripts/multi-session.sh start tests "Run all tests"

# 세션 목록
./.claude/scripts/multi-session.sh list

# 세션 연결
./.claude/scripts/multi-session.sh attach feature

# 세션 종료
./.claude/scripts/multi-session.sh stop feature
./.claude/scripts/multi-session.sh stop-all
```

### Claude Squad 사용 (권장)

```bash
# 설정 생성
./.claude/scripts/claude-squad-setup.sh config

# 워크플로우 시작
./.claude/scripts/claude-squad-setup.sh start feature

# 상태 확인
./.claude/scripts/claude-squad-setup.sh status
```

## 세션 유형

| Session | Purpose | Branch |
|---------|---------|--------|
| main | 메인 개발 | main |
| feature | 기능 개발 | feature/* |
| bugfix | 버그 수정 | bugfix/* |
| tests | 테스트 실행 | main |
| refactor | 리팩토링 | refactor/* |

## Arguments

- `$ARGUMENTS`:
  - `setup`: 병렬 개발 환경 설정
  - `start <name>`: 새 세션 시작
  - `list`: 활성 세션 목록
  - `stop <name>`: 세션 종료

## Git Worktree 활용

각 세션은 독립적인 git worktree에서 작업:
```
.worktrees/
├── feature/     # feature 브랜치
├── bugfix/      # bugfix 브랜치
└── refactor/    # refactor 브랜치
```

## Key Files

- `.claude/scripts/multi-session.sh` - tmux 기반 관리
- `.claude/scripts/claude-squad-setup.sh` - Claude Squad 통합
- `.claude-squad.yaml` - Claude Squad 설정 (생성됨)
