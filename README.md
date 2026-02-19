# Creator Onboarding Agent

AI 기반 크리에이터 온보딩 평가 시스템. LangGraph 오케스트레이션과 멀티 에이전트 아키텍처를 활용하여 SNS 크리에이터의 적합성을 자동으로 분석하고, 최적의 미션을 추천합니다.

## 주요 기능

- **크리에이터 평가**: Instagram/TikTok/YouTube 프로필 스크래핑, 메트릭 추출, RAG 기반 유사 크리에이터 검색, S/A/B/C/D 등급 산정
- **미션 추천**: 크리에이터 특성 기반 최적 미션 매칭 (Rule-based + LLM 하이브리드)
- **역량 진단**: ML 기반(RandomForest) 학습자 역량 진단 및 맞춤형 학습 추천
- **Deep Agents**: 복잡한 질의에 대한 다단계 추론 및 자기 비평(Self-Critique) 기반 품질 향상
- **RAG 파이프라인**: 하이브리드 검색(Vector + Keyword) → Reranking → SSE 스트리밍 응답
- **외부 데이터 수집**: NILE, MOHW, KICCE API + YouTube/MCP 연동
- **다국어 지원**: 한국어/영어 UI

## 기술 스택

| Layer | Technology |
|-------|------------|
| **Backend** | FastAPI (Python 3.11+), LangGraph, LangChain |
| **LLM** | Claude Sonnet 4.5, GPT-5.2, Gemini 2.5 Flash (멀티 모델 라우팅) |
| **Embedding** | Voyage-3 (기본), text-embedding-3-large, SentenceTransformer (폴백) |
| **Vector DB** | Pinecone (프로덕션), ChromaDB (로컬) |
| **Database** | PostgreSQL, Redis |
| **Task Queue** | Celery + Flower |
| **MCP Gateway** | Express.js (TypeScript) |
| **Frontend** | React 18 + TypeScript + Tailwind + Vite |
| **Monitoring** | Langfuse, Prometheus, OpenTelemetry |

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (React + Vite)                     │
│  평가 패널 │ 미션 추천 │ 분석 리포트 │ 역량진단/검색              │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                    FastAPI Gateway (Python)                      │
│  /creator │ /missions │ /analytics │ /competency │ /rag │ /mcp  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────────────┐
│                  LangGraph MainOrchestrator                      │
│                                                                  │
│  Intent Analyzer → 에이전트 라우팅                               │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ CreatorAgent │ │ MissionAgent │ │ Competency   │             │
│  │ (RAG)        │ │ (Rule+LLM)   │ │ Agent (ML)   │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ DeepAgents   │ │ SearchAgent  │ │ Analytics    │             │
│  │ (Self-Crit)  │ │ (Hybrid)     │ │ Agent        │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  RAG Pipeline: Query Expansion → Hybrid Retrieval → Rerank      │
│                → Context Build → Generation → Refine → Cache    │
└──────────┬───────────────────────────────────┬──────────────────┘
           │                                   │
    ┌──────┴──────┐                  ┌─────────┴─────────┐
    │ MCP Gateway │                  │ External Services  │
    │ (Node.js)   │                  │ Pinecone │ Langfuse│
    │ Supadata/   │                  │ Postgres │ Redis   │
    │ YouTube     │                  │ Celery   │ Prom.   │
    └─────────────┘                  └───────────────────┘
```

## 에이전트 구성

| 에이전트 | 역할 | 주요 기능 |
|---------|------|----------|
| **CreatorOnboardingAgent** | 크리에이터 평가 | 프로필 스크래핑, 메트릭 추출, RAG 유사 크리에이터 검색, 등급 산정 |
| **MissionAgent** | 미션 추천 | 크리에이터-미션 매칭, 적합도 점수, YouTube/MCP 인사이트 |
| **CompetencyAgent** | 역량 진단 | RandomForest ML 분석, 강점/약점 식별, 맞춤 학습 추천 |
| **RecommendationAgent** | 학습 추천 | 역량 수준별 학습 자료 추천, 학습 스타일 매칭 |
| **SearchAgent** | RAG 검색 | 하이브리드 검색 (Vector + Keyword), Cross-Encoder 재순위화 |
| **AnalyticsAgent** | 성과 분석 | 학습 진도, 참여도, 성과 메트릭 분석 및 리포트 |
| **DataCollectionAgent** | 데이터 수집 | NILE/MOHW/KICCE API 연동, 데이터 검증 및 영속화 |
| **DeepAgents** | 심층 추론 | 다단계 추론, Self-Critique 기반 품질 향상 |

## 디렉토리 구조

```
creator-onboarding-agent/
├── src/
│   ├── agents/              # AI 에이전트 (9개)
│   ├── rag/                 # RAG 파이프라인 (14개 모듈)
│   ├── api/                 # FastAPI 라우트, 미들웨어, 스키마
│   ├── graphs/              # LangGraph 오케스트레이터
│   ├── services/            # MCP 통합, 인증, A/B 테스트
│   ├── mcp/                 # MCP 서버 (Vector Search, HTTP Fetch, YouTube)
│   ├── core/                # BaseAgent, Circuit Breaker, 예외
│   ├── domain/              # DDD 도메인 모델 (크리에이터, 역량, 미션)
│   ├── monitoring/          # Langfuse, Prometheus, OpenTelemetry
│   ├── tasks/               # Celery 비동기 태스크
│   ├── tools/               # 에이전트 도구 (벡터 검색, 역량 분석)
│   ├── data/models/         # Pydantic 데이터 모델
│   └── app/                 # FastAPI 앱 진입점
├── config/settings.py       # Pydantic Settings (환경 설정)
├── node/                    # Node.js MCP Gateway (Express + TypeScript)
├── frontend/                # React 프론트엔드
├── tests/                   # unit / integration / e2e
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (선택)

### 환경 변수 설정

```bash
cp .env.example .env
```

필수 환경 변수:

```env
# LLM API Keys
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
VOYAGE_API_KEY=pa-...

# Vector DB
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=creator-onboarding

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_learning_db
REDIS_URL=redis://localhost:6379/0

# Authentication
SECRET_KEY=your-secret-key

# MCP (선택)
SUPADATA_API_KEY=...

# Observability (선택)
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

전체 환경 변수 목록은 `.env.example`을 참조하세요.

### 로컬 개발

```bash
# Backend (Python)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn src.app.main:app --reload --port 8000

# MCP Gateway (Node.js)
cd node && npm install && npm run dev

# Frontend
cd frontend && npm install && npm run dev
```

### Docker 실행

```bash
docker-compose up -d                              # 전체 서비스
docker-compose --profile monitoring up -d          # 모니터링 포함
docker-compose up -d api postgres redis            # 최소 구성
```

| 서비스 | 포트 | 설명 |
|--------|------|------|
| api | 8000 | FastAPI 백엔드 |
| mcp-gateway | 3001 | Node.js MCP 서버 |
| postgres | 5432 | PostgreSQL |
| redis | 6379 | Redis 캐시/세션 |
| celery-worker | - | 백그라운드 작업 |
| flower | 5555 | Celery 모니터링 (선택) |

## API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/creator/evaluate` | 크리에이터 평가 (등급 산정) |
| POST | `/api/v1/missions/recommend` | 미션 추천 |
| POST | `/api/v1/competency/diagnose` | 역량 진단 |
| GET | `/api/v1/rag/query/stream` | RAG 쿼리 (SSE 스트리밍) |
| POST | `/api/v1/mcp/hybrid-search` | MCP 하이브리드 검색 |
| GET | `/api/v1/session/{id}` | 세션 상태 조회 |
| GET | `/api/v1/analytics/report` | 성과 분석 리포트 |
| GET | `/health` | 헬스체크 |

API 문서: `http://localhost:8000/docs` (Swagger UI)

## 개발 가이드

### 새 에이전트 추가

1. `src/agents/`에 모듈 생성
2. `BaseAgent` 상속, `async execute()` 구현
3. `config/settings.py`의 `AGENT_MODEL_CONFIGS`에 등록
4. 오케스트레이터에 라우팅 추가

### 테스트

```bash
pytest tests/                        # 전체 테스트
pytest --cov=src tests/              # 커버리지 포함
pytest tests/unit/agents/ -v         # 에이전트 테스트
```

### 코드 스타일

```bash
ruff check src/ && ruff format src/  # 린팅 + 포맷팅
mypy src/                            # 타입 체크
```

## 라이선스

MIT License
