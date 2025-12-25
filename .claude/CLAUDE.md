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
- **Testing**: pytest 95% coverage, Cypress E2E

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
│   └── data-analyst.md
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
└── hooks/                 # 이벤트 훅 스크립트
    ├── format-python.sh
    ├── validate-json.sh
    └── security-check.sh
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
