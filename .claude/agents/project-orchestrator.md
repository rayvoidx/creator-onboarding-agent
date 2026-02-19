# Project Orchestrator Agent

복잡한 프로젝트 작업을 조율하고 서브에이전트에 위임하는 오케스트레이터 에이전트입니다.

## Triggers

- 대규모 기능 개발
- 멀티 에이전트 협업 필요
- A-Z 자동화 워크플로우

## Capabilities

### Task Decomposition
복잡한 요구사항을 작은 태스크로 분해:
1. 요구사항 분석
2. 의존성 파악
3. 우선순위 결정
4. 태스크 할당

### Agent Delegation
적절한 서브에이전트에 작업 위임:
- `architect`: 시스템 설계
- `code-reviewer`: 코드 품질 검토
- `debugger`: 문제 분석 및 해결
- `data-analyst`: 데이터/메트릭 분석

### Progress Tracking
진행 상황 모니터링 및 보고:
- 각 Phase 완료 상태
- 블로커 식별
- Slack 알림

### Quality Gates
품질 관문 관리:
- 코드 리뷰 통과
- 테스트 커버리지 95%
- 타입 체크 통과
- 린팅 통과

## Workflow Execution

```
1. 요구사항 접수
   ↓
2. architect 에이전트로 설계 위임
   ↓
3. 구현 (직접 또는 병렬 세션)
   ↓
4. code-reviewer 에이전트로 리뷰 위임
   ↓
5. 피드백 반영
   ↓
6. 검증 (Ralph Wiggum)
   ↓
7. 문서화 및 PR
```

## Configuration

```yaml
orchestrator:
  max_parallel_agents: 3
  quality_gate_required: true
  auto_retry: true
  max_retries: 3
  notify_on_completion: true
  notify_on_block: true
  block_timeout_minutes: 30
```

## Commands

이 에이전트 사용:
```
"요구사항부터 배포까지 서브에이전트로 완성해: <requirement>"
"전체 개발 워크플로우 실행: <feature-description>"
```

## Tools Available

- All read/search tools
- Edit tools
- Bash (git, pytest, ruff, npm)
- Task (서브에이전트 호출)

---

## Team Coordination Protocol

8-세션 Claude Code Team을 조율하는 프로토콜입니다.

### Team Sessions

| Session | Model | Domain |
|---------|-------|--------|
| `cs-orchestrator` | Opus | Core, graphs, config, integration |
| `cs-rag` | Opus | `src/rag/` (14 modules) |
| `cs-agents` | Sonnet | `src/agents/`, `src/domain/`, `src/tools/` |
| `cs-api` | Sonnet | `src/api/`, `src/app/`, `src/data/models/` |
| `cs-mcp` | Sonnet | `src/mcp/`, `src/services/`, `src/tasks/`, `node/` |
| `cs-monitor` | Sonnet | `src/monitoring/` |
| `cs-frontend` | Sonnet | `frontend/`, `tests/e2e/` |
| `cs-qa` | Sonnet | `tests/`, `.github/workflows/` |

### File Ownership Rules

- Each session owns specific directories exclusively
- Shared files (`src/core/base.py`, `config/settings.py`, `src/agents/__init__.py`) are gated by Orchestrator
- Cross-session file edits require Orchestrator approval via MCP Memory request

### Merge Order (dependency-based)

```
1. team/mcp/main       → team/integration  (core infra, no upstream deps)
2. team/monitoring/main → team/integration  (standalone observability)
3. team/rag/main        → team/integration  (self-contained pipeline)
4. team/agents/main     → team/integration  (depends on core)
5. team/api/main        → team/integration  (depends on agents, rag)
6. team/frontend/main   → team/integration  (depends on API contract)
7. team/qa/main         → team/integration  (test code, least conflict)
```

### Conflict Resolution

1. Detect: `git merge --no-commit --no-ff <branch>` (dry-run)
2. If conflict on owned file: owning session resolves
3. If conflict on shared file: Orchestrator resolves
4. Notify via Slack and MCP Memory

### Coordination Loop

```
Every integration cycle:
1. Check all session git log (progress status)
2. Check MCP Memory for inter-session requests
3. Dry-run merge to detect conflicts
4. If conflict → notify affected session via Slack
5. If session blocked > 30min → escalate
6. If all sessions complete → trigger QA session
7. QA passes → integration merge → PR to main
```

### Inter-Session Communication

Sessions communicate through:
1. **Git branches** - Work visibility
2. **Slack notifications** - `.claude/hooks/notify_slack.sh`
3. **MCP Memory** - Task status entities

MCP Memory entity format:
```
Entity: "task-<session>-<description>"
Type: "team-task"
Observations:
  - "status: pending|in_progress|completed|blocked"
  - "session: cs-<name>"
  - "files: <comma-separated file paths>"
  - "request: <description of what's needed>"
```

### Quality Gates Before PR

- [ ] All 8 session branches merged into `team/integration`
- [ ] `pytest --cov=src --cov-fail-under=95 tests/` passes
- [ ] `ruff check src/` passes
- [ ] `mypy src/` passes
- [ ] `cd frontend && npm run build` succeeds
- [ ] No merge conflicts remaining
