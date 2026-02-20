# Creator Onboarding Agent

AI 기반 크리에이터 온보딩 및 미션 추천 시스템

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
├─────────────────────────────────────────────────────────────┤
│                    FastAPI Application                      │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Creator │  │ Mission │  │Analytics│  │   RAG   │        │
│  │  Agent  │  │  Agent  │  │  Agent  │  │Pipeline │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       └────────────┴────────────┴────────────┘              │
│                         │                                   │
│  ┌──────────────────────┴───────────────────────┐          │
│  │              LangGraph Orchestrator           │          │
│  └──────────────────────┬───────────────────────┘          │
├──────────────────────────┼──────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐│┌─────────┐  ┌─────────┐         │
│  │Pinecone │  │ Voyage  │││Langfuse │  │Prometheus│         │
│  │(Vector) │  │(Embed)  │││(Trace)  │  │(Metrics)│         │
│  └─────────┘  └─────────┘│└─────────┘  └─────────┘         │
└──────────────────────────┴──────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI, Pydantic v2, LangGraph |
| LLM | Claude Sonnet 4.5, GPT-5.2, Gemini 2.5 Flash |
| Embedding | Voyage-3, text-embedding-3-large |
| Vector DB | Pinecone |
| Monitoring | Langfuse, Prometheus, Grafana |

## Coding Standards

- **Agents**: `BaseAgent` 상속, `async execute()` 메서드 구현
- **RAG**: Hybrid retrieval → Rerank (0.85) → Refine → SSE
- **API**: Pydantic v2 스키마, `Depends()` 의존성 주입, Circuit Breaker
- **Testing**: pytest (target 95% coverage), Cypress E2E

## Goals

- [ ] 테스트 커버리지: 90% → 95%
- [ ] 토큰 사용량: 40% 절감
- [ ] 에이전트 확장: 8개 → 12개

---

## Claude Code 기능 구성

### 📁 폴더 구조

```
.claude/
├── CLAUDE.md              # 프로젝트 문서 (이 파일)
├── settings.json          # 프로젝트 설정 (공유됨)
├── settings.local.json    # 개인 설정 (gitignore)
│
├── commands/              # 슬래시 커맨드 (/command)
│   ├── rag-tuner.md
│   ├── mcp-optimizer.md
│   ├── test-agent.md
│   ├── perf-agent.md
│   ├── security-agent.md
│   ├── docs-agent.md
│   ├── abtest-agent.md
│   └── monitor-agent.md
│
├── agents/                # 자동 위임 서브에이전트
│   ├── code-reviewer.md
│   ├── debugger.md
│   ├── architect.md
│   ├── data-analyst.md
│   ├── test-runner.md
│   ├── doc-updater.md
│   └── project-orchestrator.md
│
├── skills/                # 자동 활성화 스킬
│   ├── rag-optimization/
│   │   └── SKILL.md
│   ├── api-development/
│   │   └── SKILL.md
│   ├── testing/
│   │   └── SKILL.md
│   └── monitoring/
│       └── SKILL.md
│
├── team/                  # Claude Squad 세션별 지침
│   ├── orchestrator.md
│   ├── rag.md
│   ├── agents.md
│   ├── api.md
│   ├── mcp.md
│   ├── monitor.md
│   ├── frontend.md
│   └── qa.md
│
├── hooks/                 # 이벤트 훅 스크립트
│   ├── notify_slack.sh
│   ├── format_after_edit.sh
│   ├── validate-json.sh
│   └── security-check.sh
│
└── scripts/               # 자동화 스크립트
    ├── auto-dev-orchestrator.sh
    ├── auto-verify.sh
    ├── ralph-wiggum.sh
    ├── multi-session.sh
    └── claude-squad-setup.sh
```

---

## Commands (슬래시 커맨드)

사용자가 `/command` 형식으로 직접 호출하는 커맨드:

| Command | Description |
|---------|-------------|
| `/rag-tuner` | RAG 파이프라인 최적화 (threshold, multi-query) |
| `/mcp-optimizer` | MCP 벡터 인덱스 최적화 |
| `/test-agent` | pytest 95% + Cypress E2E 테스트 |
| `/perf-agent` | Prometheus alerting, auto-scaling |
| `/security-agent` | API rate-limit, MCP 보안 감사 |
| `/docs-agent` | OpenAPI/Swagger 문서 자동화 |
| `/abtest-agent` | Creator 추천 A/B 테스트 |
| `/monitor-agent` | Langfuse → Grafana 대시보드 |

**사용 예시:**
```bash
/rag-tuner "rerank threshold 0.85, multi-query 5"
/test-agent "increase coverage for src/rag/ to 95%"
/perf-agent "setup alerting for P99 latency > 500ms"
```

---

## Agents (서브에이전트)

Claude가 자동으로 위임하는 전문 에이전트:

| Agent | Trigger | Model |
|-------|---------|-------|
| `code-reviewer` | 코드 변경, PR 리뷰 | Sonnet |
| `debugger` | 에러, 버그 분석 | Sonnet |
| `architect` | 설계, 기술 결정 | Opus |
| `data-analyst` | 데이터 분석, 메트릭 | Sonnet |
| `test-runner` | 테스트 실행, 커버리지 | Sonnet |
| `doc-updater` | 문서 업데이트, API 문서 | Haiku |
| `project-orchestrator` | A-Z 워크플로우 조율 | Opus |

---

## Skills (자동 스킬)

컨텍스트에 따라 자동 활성화되는 스킬:

| Skill | Trigger Keywords |
|-------|-----------------|
| `rag-optimization` | retrieval, rerank, embedding, vector search |
| `api-development` | endpoint, route, schema, pydantic, fastapi |
| `testing` | pytest, test, coverage, mock, fixture |
| `monitoring` | trace, metric, log, alert, dashboard |

---

## Hooks (이벤트 훅)

도구 호출 전후에 자동 실행되는 훅:

| Event | Action |
|-------|--------|
| `PreToolUse(Edit)` | 편집 로그 기록 |
| `PostToolUse(Write)` | Python 구문 검증 |
| `Stop` | 세션 완료 로그 |

**커스텀 훅 스크립트:**
- `format-python.sh` - ruff로 Python 포맷팅
- `validate-json.sh` - JSON 구문 검증
- `security-check.sh` - 위험 명령 차단

---

## Settings (설정)

### Permissions (권한)

**허용:**
- Python/pytest/git/npm 명령
- src/, tests/, config/ 파일 읽기/편집

**차단:**
- .env 파일 접근
- secrets, credentials 파일
- rm -rf 명령

**확인 필요:**
- docker, curl 명령
- .claude/ 파일 편집

---

## Key Directories

```
src/
├── agents/           # LangGraph 에이전트
├── api/v1/routes/    # FastAPI 엔드포인트
├── rag/              # RAG 파이프라인
├── mcp/              # MCP 서버 통합
├── monitoring/       # Langfuse, Prometheus
└── services/         # 비즈니스 로직

tests/
├── unit/             # 단위 테스트
├── integration/      # 통합 테스트
└── e2e/              # E2E 테스트
```

## Quick Commands

```bash
# 개발 서버
uvicorn main:app --reload --port 8000

# 테스트
pytest --cov=src tests/

# 프론트엔드
cd frontend && npm run dev
```

---

## Agentic Development Architecture

완전 자동화된 개발 워크플로우를 위한 3-레인 아키텍처:

```
┌─────────────────────────────────────────────────────────────────┐
│                    NOTIFICATION BUS (Slack)                     │
│         입력 대기 / 권한 요청 / 완료 → 모바일 푸시              │
└────────────────────────────┬────────────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  LOCAL LANE   │   │  GITHUB LANE  │   │  WEB/MOBILE   │
│               │   │               │   │               │
│ • Claude Squad│   │ • @claude 멘션│   │ • claude.ai   │
│   (cs CLI)    │   │ • PR 자동생성 │   │ • 비동기 작업 │
│ • 8 병렬 세션 │   │ • 백그라운드  │   │ • 이슈 생성   │
│ • git worktree│   │   실행        │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

### 운영 루틴

1. **폰에서 이슈 생성** → @claude 멘션
2. **GitHub Action 실행** → 코드 수정 → PR 생성
3. **Slack 푸시** → 진행/권한요청/완료 알림
4. **PR 리뷰** → 승인/수정 지시

---

## Hooks (이벤트 훅) - 업데이트

stdin으로 JSON payload를 수신하는 Hook 시스템:

| Event | Trigger | Action |
|-------|---------|--------|
| `Notification` | 입력/상태 변경 | Slack 알림 |
| `PermissionRequest` | 권한 필요 | Slack 알림 |
| `PostToolUse(Edit\|Write)` | 파일 수정 후 | 자동 포맷팅 |
| `PreToolUse(Edit)` | 편집 전 | 로그 기록 |
| `Stop` | 세션 종료 | 완료 알림 |

**Hook 스크립트:**
- `notify_slack.sh` - JSON stdin 파싱 → Slack 푸시
- `format_after_edit.sh` - 파일 타입별 자동 포맷 (ruff/prettier)

---

## GitHub Action (claude-code-action)

`.github/workflows/claude-code.yml` - 백그라운드 자동 개발

**트리거:**
- 이슈/PR에서 `@claude` 멘션
- `claude` 라벨 추가

**기능:**
- 코드 수정 → PR 생성/업데이트
- 테스트 실행 → 결과 코멘트
- Slack 완료 알림

**사용법:**
```markdown
@claude 사용자 인증 기능을 JWT 기반으로 구현해주세요.
- FastAPI 엔드포인트 추가
- pytest 테스트 포함
- 95% 커버리지 유지
```

**Secrets 필요:**
- `ANTHROPIC_API_KEY`
- `SLACK_WEBHOOK_URL` (선택)

---

## Claude Squad (팀 병렬 개발)

Claude Squad(`cs`)로 8-세션 병렬 개발 팀을 운영합니다.

```bash
# 설치
brew install smtg-ai/tap/claude-squad

# 실행
cs

# TUI Key Bindings:
#   n/N   새 인스턴스 생성
#   ↑/↓   인스턴스 이동
#   Enter  인스턴스 접속
#   c     커밋 & 일시정지
#   s     커밋 & 푸시
#   D     인스턴스 삭제
#   q     종료
```

### Team Sessions (7 teammates + 1 lead)

| Session | Domain | Coverage |
|---------|--------|----------|
| **Lead** | 팀 조율, 통합 | - |
| RAG Engineer | `src/rag/` | 98% |
| Agent Developer | `src/agents/`, `src/domain/` | 98% |
| API Developer | `src/api/`, `src/app/` | 100% |
| MCP/Infra | `src/mcp/`, `src/services/`, `node/` | 95% |
| Monitoring | `src/monitoring/` | 95% |
| Frontend | `frontend/`, `tests/e2e/` | 90% |
| QA Guardian | `tests/`, `.github/workflows/` | 95% |

각 세션별 상세 지침: `.claude/team/*.md`

```bash
# 세션별 프롬프트 확인
./.claude/scripts/claude-squad-setup.sh prompts
```

---

## Automation Scripts

```bash
# A-Z 자동화 워크플로우
./.claude/scripts/auto-dev-orchestrator.sh "요구사항"

# Ralph Wiggum 자동 검증 (반복 테스트)
./.claude/scripts/ralph-wiggum.sh start|stop|status

# 세션별 스코프 검증
./.claude/scripts/auto-verify.sh --session rag

# 멀티 세션 관리 (tmux fallback)
./.claude/scripts/multi-session.sh setup|start|list|stop
```

---

## 환경 변수 설정

`.env` 또는 `.env.local`:
```bash
# Slack 알림 (필수)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=#dev-notifications

# GitHub Action용
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...

# 자동화 설정
CLAUDE_MAX_ITERATIONS=10
CLAUDE_AUTO_NOTIFY=true
```

GitHub Secrets (Actions용):
- `ANTHROPIC_API_KEY`
- `SLACK_WEBHOOK_URL`
