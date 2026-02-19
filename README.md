# Creator Onboarding Agent

> **Agentic AI** 기반 크리에이터 온보딩 평가 시스템
>
> LangGraph 멀티 에이전트 오케스트레이션으로 SNS 크리에이터의 적합성을 자동 분석하고, 최적의 미션을 추천합니다.

## Why Agentic AI?

단순 LLM Chatbot이나 RAG를 넘어, **자율적으로 추론하고 행동하는 에이전트 시스템**입니다.

```
  LLM Chatbot          RAG                    Agentic AI (This Project)
  ───────────          ───                    ─────────────────────────
  Query                Query                  Query
    │                    │                      │
    ▼                    ▼                      ▼
  ┌──────┐           ┌──────────┐           ┌──────────────────────────────┐
  │System│           │Embedding │           │   Intent Analyzer (Router)   │
  │Prompt│           │          │           └──────────┬───────────────────┘
  └──┬───┘           └────┬─────┘                      │
     │                    ▼                    ┌───────┼────────┐
     │              ┌──────────┐               ▼       ▼        ▼
     │              │Vector DB │          ┌────────┐┌──────┐┌───────┐
     │              │Knowledge │          │Planner ││Agent ││Agent  │
     │              │  Base    │          │(System ││  A   ││  B    │
     │              └────┬─────┘          │   2)   │└──┬───┘└───┬───┘
     │                   ▼                └───┬────┘   │        │
     ▼              ┌────────┐                ▼        ▼        ▼
  ┌──────┐          │  Data  │          ┌──────────────────────────┐
  │ LLM  │          │Augment.│          │  Tool Use (MCP/Search)   │
  └──┬───┘          └───┬────┘          └────────────┬─────────────┘
     │                  ▼                            ▼
     │              ┌──────┐               ┌──────────────────┐
     ▼              │ LLM  │               │  Replan Loop     │──→ repeat
  Output            └──┬───┘               │  (Self-Critique) │     until
                       ▼                   └────────┬─────────┘     done
                    Output                          ▼
                                                 Output
                                           (with reasoning trace)
```

## Agentic Architecture

```
                         ┌─────────┐
                         │  User   │
                         │  Query  │
                         └────┬────┘
                              │
                    ┌─────────▼──────────┐
                    │  Intent Analyzer   │  LLM-based routing
                    │  (7 intent types)  │  to domain agents
                    └─────────┬──────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌─────────────┐   ┌──────────────┐    ┌──────────────┐
   │   Creator    │   │   Mission    │    │ Competency   │
   │   Agent      │   │   Agent      │    │   Agent      │
   │              │   │              │    │              │
   │ • Scraping   │   │ • Matching   │    │ • ML(RF)     │
   │ • Metrics    │   │ • Scoring    │    │ • Diagnosis  │
   │ • RAG Search │   │ • MCP Tools  │    │ • Learning   │
   │ • Grading    │   │ • YouTube    │    │   Recommend  │
   └──────┬───────┘   └──────┬───────┘    └──────┬───────┘
          │                  │                    │
          └──────────────────┼────────────────────┘
                             │
   ┌──────────────┐          │          ┌──────────────┐
   │  Deep Agent  │◄─────────┼─────────►│ Search Agent │
   │              │          │          │              │
   │ • Multi-step │          │          │ • Hybrid     │
   │   reasoning  │          │          │   retrieval  │
   │ • Self-      │          │          │ • Reranking  │
   │   Critique   │          │          │ • Vector+KW  │
   └──────────────┘          │          └──────────────┘
                             ▼
              ┌─────────────────────────────┐
              │       RAG Pipeline          │
              │                             │
              │  Query Expansion (5 vars)   │
              │         │                   │
              │  Hybrid Retrieval           │
              │  (Vector + BM25 + Graph)    │
              │         │                   │
              │  CrossEncoder Rerank ≥0.85  │
              │         │                   │
              │  Context Build (128K)       │
              │         │                   │
              │  Multi-Model Generation     │
              │  Claude│GPT│Gemini          │
              │         │                   │
              │  Response Refine + Cache    │
              └────────────┬────────────────┘
                           │
                    ┌──────▼──────┐
                    │ SSE Stream  │
                    │  Response   │
                    └─────────────┘
```

## Multi-Agent System

```
┌─────────────────────────────────────────────────────────────────────┐
│                                                                     │
│     User ──────► MainOrchestrator (LangGraph)                       │
│                        │                                            │
│                  ┌─────┴─────┐                                      │
│                  │  Router   │  SLM intent classification           │
│                  └─────┬─────┘                                      │
│                        │                                            │
│         ┌──────────────┼──────────────┐                             │
│         ▼              ▼              ▼                              │
│    ┌─────────┐   ┌─────────┐   ┌─────────┐                         │
│    │ Agent 1 │   │ Agent 2 │   │ Agent N │   Each agent has:       │
│    │         │   │         │   │         │   • Memory              │
│    └────┬────┘   └────┬────┘   └────┬────┘   • Tools (MCP)        │
│         │             │             │         • LLM access         │
│         └──────┬──────┘─────────────┘         • Self-evaluation    │
│                ▼                                                    │
│         ┌─────────────┐                                             │
│         │ Tool Worker │  MCP Servers: Web, YouTube, Supadata       │
│         │ (MCP)       │  Vector Search, HTTP Fetch                 │
│         └──────┬──────┘                                             │
│                │                                                    │
│         ┌──────▼──────┐                                             │
│         │  Replan     │  Self-Critique loop                        │
│         │  Loop       │  until quality threshold met               │
│         └──────┬──────┘                                             │
│                │                                                    │
│         ┌──────▼──────┐                                             │
│         │   Final     │  Synthesize agent outputs                  │
│         │ Synthesis   │  → SSE streaming response                  │
│         └─────────────┘                                             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## 주요 기능

| 기능 | 설명 | 에이전트 패턴 |
|------|------|-------------|
| **크리에이터 평가** | SNS 프로필 스크래핑, 메트릭 추출, S/A/B/C/D 등급 | RAG-enhanced + Heuristic |
| **미션 추천** | 크리에이터-미션 매칭, 적합도 점수 | Rule-based + LLM Hybrid |
| **역량 진단** | ML(RandomForest) 기반 역량 분석, 학습 추천 | ML + LLM + Security |
| **심층 추론** | 다단계 추론, Self-Critique 품질 향상 | CodeAct + ReAct |
| **RAG 검색** | 하이브리드 검색 → Reranking → SSE 스트리밍 | Compound AI System |
| **데이터 수집** | NILE/MOHW/KICCE API + YouTube/MCP | Tool-augmented Agent |

## 기술 스택

| Layer | Technology |
|-------|------------|
| **Orchestration** | LangGraph (Compound AI System), LangChain |
| **Backend** | FastAPI (Python 3.11+), Pydantic v2 |
| **LLM Fleet** | Claude Sonnet 4.5 + GPT-5.2 + Gemini 2.5 Flash |
| **Embedding** | Voyage-3, text-embedding-3-large, SentenceTransformer |
| **Vector DB** | Pinecone (prod), ChromaDB (dev) |
| **MCP Gateway** | Express.js (TypeScript) — YouTube, Web, Supadata |
| **Database** | PostgreSQL, Redis |
| **Frontend** | React 18 + TypeScript + Tailwind + Vite |
| **Monitoring** | Langfuse (LLM tracing), Prometheus, OpenTelemetry |
| **Task Queue** | Celery + Flower |

## 에이전트 구성 (9 Agents)

| Agent | Pattern | 기능 |
|-------|---------|------|
| **CreatorOnboardingAgent** | RAG + Heuristic | 프로필 스크래핑, 유사 크리에이터 검색, 등급 산정 |
| **MissionAgent** | Rule + LLM + MCP | 크리에이터-미션 매칭, YouTube/MCP 인사이트 |
| **CompetencyAgent** | ML + LLM | RandomForest 역량 분석, 강점/약점 식별 |
| **RecommendationAgent** | LLM | 역량 수준별 학습 자료 추천 |
| **SearchAgent** | Hybrid Retrieval | Vector + Keyword + CrossEncoder Reranking |
| **AnalyticsAgent** | LLM + Data | 학습 진도, 참여도, 성과 메트릭 리포트 |
| **DataCollectionAgent** | Tool-augmented | NILE/MOHW/KICCE API 연동, 데이터 검증 |
| **DeepAgents** | ReAct + Self-Critique | 다단계 추론, 품질 반복 향상 |
| **IntegrationAgent** | Coordinator | 크로스 에이전트 통합 |

## 디렉토리 구조

```
creator-onboarding-agent/
├── src/
│   ├── agents/              # 9 AI Agents (BaseAgent pattern)
│   ├── rag/                 # RAG Pipeline (14 modules)
│   ├── graphs/              # LangGraph Orchestrator
│   ├── api/                 # FastAPI routes + middleware
│   ├── mcp/                 # MCP Servers (Vector, HTTP, YouTube)
│   ├── services/            # MCP integration, auth, A/B testing
│   ├── core/                # BaseAgent, Circuit Breaker
│   ├── domain/              # DDD models (creator, competency, mission)
│   ├── monitoring/          # Langfuse, Prometheus, OpenTelemetry
│   ├── tasks/               # Celery async tasks
│   ├── tools/               # Agent tools (vector search, ML)
│   └── app/                 # FastAPI entrypoint
├── node/                    # MCP Gateway (Express + TypeScript)
├── frontend/                # React 18 + Tailwind + Vite
├── config/settings.py       # Pydantic Settings
├── tests/                   # unit / integration / e2e
├── docker-compose.yml       # Full-stack Docker setup
└── Dockerfile               # Multi-stage Python build
```

## Quick Start

### 환경 변수

```bash
cp .env.example .env
# .env 파일에 API 키 설정
```

```env
# Required
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
VOYAGE_API_KEY=pa-...
PINECONE_API_KEY=...
SECRET_KEY=your-secret-key

# Optional
SUPADATA_API_KEY=...
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

### Docker (권장)

```bash
docker-compose up -d
```

| 서비스 | 포트 | 설명 |
|--------|------|------|
| **frontend** | [localhost:3000](http://localhost:3000) | React UI |
| **api** | [localhost:8001](http://localhost:8001) | FastAPI Backend |
| **mcp-gateway** | 3001 | MCP Server (Node.js) |
| postgres | 5432 | PostgreSQL |
| redis | 6379 | Redis Cache |
| celery-worker | - | Background Tasks |

### 로컬 개발

```bash
# Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000

# MCP Gateway
cd node && npm install && npm run dev

# Frontend
cd frontend && npm install && npm run dev
```

## API Endpoints

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/creator/evaluate` | 크리에이터 평가 |
| POST | `/api/v1/missions/recommend` | 미션 추천 |
| POST | `/api/v1/competency/diagnose` | 역량 진단 |
| GET | `/api/v1/rag/query/stream` | RAG 쿼리 (SSE) |
| POST | `/api/v1/mcp/hybrid-search` | 하이브리드 검색 |
| GET | `/api/v1/session/{id}` | 세션 조회 |
| GET | `/health` | 헬스체크 |

API 문서: [localhost:8001/docs](http://localhost:8001/docs) (Swagger UI)

## 라이선스

MIT License
