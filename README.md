# Creator Onboarding Agent

AI 기반 크리에이터 온보딩 평가 시스템. LangGraph 오케스트레이션과 멀티 에이전트 아키텍처를 활용하여 SNS 크리에이터의 적합성을 자동으로 분석하고, 최적의 미션을 추천합니다.

## 주요 기능

- **크리에이터 평가**: Instagram/TikTok/YouTube 프로필 자동 스크래핑 및 메트릭 추출, RAG 기반 유사 크리에이터 검색
- **등급 산정**: S/A/B/C/D 등급과 세부 점수 (콘텐츠 품질, 참여도, 브랜드 적합성)
- **미션 추천**: 크리에이터 특성 기반 최적 미션 매칭 (Rule-based + LLM 하이브리드)
- **역량 진단**: ML 기반(RandomForest + scikit-learn) 학습자 역량 진단 및 맞춤형 학습 추천
- **Deep Agents**: 복잡한 질의에 대한 다단계 추론 및 자기 비평(Self-Critique) 기반 품질 향상
- **인사이트 리포트**: RAG 파이프라인을 통한 심층 분석, YouTube 채널 분석 연동
- **외부 데이터 수집**: 국가평생교육진흥원(NILE), 보건복지부(MOHW), 육아정책연구소(KICCE) API 연동
- **다국어 지원**: 한국어/영어 UI

## 기술 스택

### Backend (Python)
- **Framework**: FastAPI (Python 3.11+)
- **AI Orchestration**: LangGraph 0.2.x, LangChain 0.3.x
- **LLM**: Claude Sonnet 4.5 (claude-sonnet-4-5-20250929), GPT-5.2, Gemini 2.5 Flash (멀티 모델 플릿)
- **Embeddings**: Voyage AI voyage-3 (기본), OpenAI text-embedding-3-large, Gemini text-embedding-004
- **Vector DB**: Pinecone (프로덕션), ChromaDB (로컬 개발용)
- **Database**: PostgreSQL, Redis (캐싱)
- **Task Queue**: Celery + Flower (모니터링)
- **ML/DL**: scikit-learn, PyTorch, sentence-transformers

### Backend (Node.js)
- **Framework**: Express.js (TypeScript)
- **Purpose**: MCP Gateway, LLM Manager Agent, Enterprise Briefing Agent
- **Integration**: Python API 클라이언트를 통한 에이전트 연동

### Frontend
- **Framework**: React 18 + TypeScript
- **UI Library**: Tailwind CSS, shadcn/ui
- **State Management**: TanStack Query
- **i18n**: react-i18next
- **Build Tool**: Vite

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Cloud**: Naver Cloud Platform (NCP) 지원
- **Monitoring**: Prometheus, Langfuse (LLM observability), OpenTelemetry
- **Authentication**: JWT (OAuth2 compatible)

## 아키텍처

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Frontend (React + Vite)                            │
│  ┌──────────┐  ┌────────────────┐  ┌──────────────┐  ┌───────────────────┐ │
│  │ 평가 패널 │  │ 미션 추천 패널  │  │ 분석 리포트   │  │ 역량진단/검색 패널 │ │
│  └────┬─────┘  └───────┬────────┘  └──────┬───────┘  └─────────┬─────────┘ │
└───────┼────────────────┼──────────────────┼────────────────────┼───────────┘
        │                │                  │                    │
        ▼                ▼                  ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FastAPI Gateway (Python)                             │
│  /api/v1/creator │ /api/v1/missions │ /api/v1/analytics │ /api/v1/competency │
│  /api/v1/rag     │ /api/v1/search   │ /api/v1/session   │ /api/v1/monitoring │
└────────┬─────────────────┬──────────────────┬─────────────────┬─────────────┘
         │                 │                  │                 │
         ▼                 ▼                  ▼                 ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                     LangGraph MainOrchestrator                               │
│  ┌──────────────────────────────────────────────────────────────────────┐    │
│  │                    Intent Analyzer (LLM-based Routing)               │    │
│  └──────────────────────────────────────────────────────────────────────┘    │
│                                    │                                         │
│           ┌────────────────────────┼────────────────────────┐                │
│           ▼                        ▼                        ▼                │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────┐       │
│  │ CreatorAgent    │    │ MissionAgent    │    │ CompetencyAgent     │       │
│  │ (RAG-enhanced)  │    │ (Rule+LLM+MCP)  │    │ (ML+LLM+Security)   │       │
│  └─────────────────┘    └─────────────────┘    └─────────────────────┘       │
│           │                        │                        │                │
│  ┌────────┴────────────────────────┴────────────────────────┴────────────┐   │
│  │                    Shared Processing Layer                            │   │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────────┐  │   │
│  │  │ DeepAgents  │ │SearchAgent  │ │Analytics    │ │DataCollection   │  │   │
│  │  │ (Self-Crit) │ │(Hybrid+Re-  │ │Agent        │ │Agent (NILE/     │  │   │
│  │  │             │ │ rank)       │ │             │ │MOHW/KICCE)      │  │   │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────────┘  │   │
│  └───────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌───────────────────────────────────┴────────────────────────────────────┐  │
│  │                     RAG Pipeline (Wrtn-style)                          │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │  │
│  │  │QueryExpander │ │RetrievalEng. │ │ContextBuilder│ │ResponseRefiner│  │  │
│  │  │(Multi-Query) │ │(Hybrid+Rerank│ │(Structured)  │ │(Hallucination │  │  │
│  │  │              │ │ CrossEncoder)│ │              │ │ Check)        │  │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                    │  │
│  │  │SemanticCache │ │PromptOptim. │ │LLMManager    │                     │  │
│  │  │(Query-based) │ │(Token Reduc.)│ │(Cost/Latency)│                    │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘                    │  │
│  └────────────────────────────────────────────────────────────────────────┘  │
└────────┬──────────────────────────────────────────────────┬──────────────────┘
         │                                                  │
         ▼                                                  ▼
┌────────────────────────────────┐    ┌───────────────────────────────────────┐
│     Node.js MCP Gateway        │    │           External Services            │
│  ┌──────────────────────────┐  │    │  ┌─────────────┐ ┌─────────────────┐  │
│  │ LLMManagerAgent          │  │    │  │ Pinecone    │ │ Langfuse        │  │
│  │ EnterpriseBriefingAgent  │  │    │  │ Vector DB   │ │ LLM Tracing     │  │
│  └──────────────────────────┘  │    │  └─────────────┘ └─────────────────┘  │
│  ┌──────────────────────────┐  │    │  ┌─────────────┐ ┌─────────────────┐  │
│  │ Supadata MCP             │  │    │  │ PostgreSQL  │ │ Redis           │  │
│  │ (YouTube/SNS Scraping)   │  │    │  │ (Metadata)  │ │ (Cache/Session) │  │
│  └──────────────────────────┘  │    │  └─────────────┘ └─────────────────┘  │
└────────────────────────────────┘    │  ┌─────────────┐ ┌─────────────────┐  │
                                      │  │ Celery      │ │ Prometheus      │  │
                                      │  │ (Tasks)     │ │ (Metrics)       │  │
                                      │  └─────────────┘ └─────────────────┘  │
                                      └───────────────────────────────────────┘
```

## 에이전트 구성

| 에이전트 | 역할 | 주요 기능 |
|---------|------|----------|
| **CreatorOnboardingAgent** | 크리에이터 평가 | 프로필 스크래핑, 메트릭 추출, RAG 기반 유사 크리에이터 검색, 등급 산정 |
| **MissionAgent** | 미션 추천 | 크리에이터-미션 매칭, 적합도 점수 계산, YouTube/MCP 인사이트 연동 |
| **CompetencyAgent** | 역량 진단 | RandomForest ML 분석, 강점/약점 식별, 개인정보 익명화, 맞춤형 학습 추천 |
| **RecommendationAgent** | 학습 추천 | 역량 수준별 학습 자료 추천, 학습 스타일 매칭 |
| **SearchAgent** | RAG 검색 | 하이브리드 검색 (Vector + Keyword), Cross-Encoder 재순위화 |
| **AnalyticsAgent** | 성과 분석 | 학습 진도, 참여도, 성과 메트릭 분석 및 리포트 생성 |
| **DataCollectionAgent** | 데이터 수집 | 외부 API 연동 (NILE, MOHW, KICCE), 데이터 검증 및 영속화 |
| **LLMManagerAgent** | LLM 관리 | 멀티 모델 선택, Cost/Latency 라우팅, 폴백 체인 |

## RAG 파이프라인 구성 (Wrtn-style)

| 컴포넌트 | 역할 | 주요 기능 |
|---------|------|----------|
| **QueryExpander** | 쿼리 확장 | Multi-Query 생성 (3개 변형), 검색 커버리지 향상 |
| **RetrievalEngine** | 하이브리드 검색 | Vector(Pinecone/Voyage) + Keyword 병렬 검색, Cross-Encoder Reranking |
| **ContextPromptBuilder** | 컨텍스트 구성 | 시스템/사용자/에이전트/RAG/히스토리 섹션 조합 |
| **IntentAnalyzer** | 의도 분석 | LLM 기반 의도 분류 (7개 카테고리), 라우팅 결정 |
| **ResponseRefiner** | 응답 정제 | Hallucination 검증, 페르소나/톤 적용, 출처 추가 |
| **SemanticCache** | 시맨틱 캐시 | 쿼리 기반 응답 캐싱, 중복 요청 최적화 |
| **PromptOptimizer** | 프롬프트 최적화 | 토큰 절감, 프롬프트 압축 |
| **LLMManager** | LLM 라우팅 | 사용자 티어/복잡도 기반 모델 선택 |
| **GenerationEngine** | 응답 생성 | 스트리밍 지원, 재시도 로직, 폴백 체인 |

## 디렉토리 구조

```
creator-onboarding-agent/
├── src/
│   ├── agents/                       # AI 에이전트
│   │   ├── __init__.py              # 에이전트 exports
│   │   ├── base.py                  # 에이전트 베이스 클래스
│   │   ├── orchestrator.py          # LangGraph 메인 오케스트레이터
│   │   ├── llm_manager_agent.py     # LLM 선택 및 관리 에이전트
│   │   ├── creator_onboarding_agent/# 크리에이터 평가 (RAG-enhanced)
│   │   ├── mission_agent/           # 미션 추천 (MCP 연동)
│   │   ├── competency_agent/        # 역량 진단 (ML+LLM+Security)
│   │   ├── recommendation_agent/    # 학습 추천
│   │   ├── search_agent/            # RAG 하이브리드 검색
│   │   ├── analytics_agent/         # 성과 분석 리포트
│   │   └── data_collection_agent/   # 외부 데이터 수집 + 영속화
│   │
│   ├── rag/                         # RAG 파이프라인 (Wrtn-style)
│   │   ├── rag_pipeline.py         # 메인 RAG 파이프라인
│   │   ├── retrieval_engine.py     # 하이브리드 검색 + Reranking
│   │   ├── generation_engine.py    # LLM 응답 생성 (스트리밍)
│   │   ├── context_builder.py      # 컨텍스트 프롬프트 빌더
│   │   ├── response_refiner.py     # 응답 정제 + Hallucination 검증
│   │   ├── intent_analyzer.py      # LLM 기반 의도 분석
│   │   ├── query_expander.py       # 쿼리 확장 (Multi-Query)
│   │   ├── semantic_cache.py       # 시맨틱 캐싱
│   │   ├── prompt_optimizer.py     # 프롬프트 최적화
│   │   ├── llm_manager.py          # LLM 라우팅 매니저
│   │   ├── batch_processor.py      # 배치 처리
│   │   ├── document_processor.py   # 문서 처리
│   │   └── prompt_templates.py     # 프롬프트 템플릿
│   │
│   ├── api/                         # FastAPI 라우트
│   │   ├── v1/routes/              # API v1 엔드포인트
│   │   │   ├── health.py           # 헬스체크
│   │   │   ├── competency.py       # 역량 진단 API
│   │   │   ├── recommendations.py  # 추천 API
│   │   │   ├── search.py           # 검색 API
│   │   │   ├── analytics.py        # 분석 API
│   │   │   ├── missions.py         # 미션 API
│   │   │   ├── rag.py              # RAG API (SSE 스트리밍)
│   │   │   ├── llm.py              # LLM 관리 API
│   │   │   ├── session.py          # 세션 관리 API
│   │   │   ├── circuit_breaker.py  # 서킷 브레이커 API
│   │   │   └── monitoring.py       # 모니터링 API
│   │   ├── routes/                 # 기타 라우트
│   │   │   └── mcp_routes.py       # MCP 라우트
│   │   ├── middleware/             # 미들웨어
│   │   │   ├── auth.py             # JWT 인증
│   │   │   ├── rate_limit.py       # Rate Limiting (Redis 지원)
│   │   │   ├── correlation.py      # 요청 추적
│   │   │   ├── error_handler.py    # 에러 핸들링
│   │   │   └── security_utils.py   # 보안 유틸리티
│   │   └── schemas/                # Pydantic 스키마
│   │       ├── request_schemas.py  # 요청 스키마
│   │       └── response_schemas.py # 응답 스키마
│   │
│   ├── services/                    # 비즈니스 로직
│   │   ├── mcp_integration.py      # MCP 통합 서비스
│   │   ├── supadata_mcp.py         # Supadata MCP 서비스
│   │   ├── auth_service.py         # 인증 서비스
│   │   ├── audit_service.py        # 감사 서비스
│   │   ├── creator_history_service.py # 크리에이터 이력 관리
│   │   ├── ab_testing_service.py   # A/B 테스트 서비스
│   │   ├── auth/                   # 인증 모듈
│   │   ├── audit/                  # 감사 모듈
│   │   ├── history/                # 이력 모듈
│   │   ├── ab_testing/             # A/B 테스트 모듈
│   │   └── creator_history/        # 크리에이터 이력 모듈
│   │
│   ├── mcp/                         # MCP 서버
│   │   ├── mcp.py                  # MCP 메인 모듈
│   │   ├── servers/                # MCP 서버 구현
│   │   │   ├── base_server.py      # 베이스 서버
│   │   │   ├── vector_search_server.py
│   │   │   └── http_fetch_server.py
│   │   └── youtube_analyzer.py     # YouTube 분석기
│   │
│   ├── core/                        # 핵심 유틸리티
│   │   ├── base.py                 # BaseAgent, BaseState 클래스
│   │   ├── exceptions.py           # 커스텀 예외
│   │   ├── circuit_breaker.py      # 서킷 브레이커 (pybreaker)
│   │   ├── patterns/               # 디자인 패턴
│   │   │   └── circuit_breaker.py
│   │   └── utils/                  # 유틸리티
│   │       ├── agent_config.py     # 에이전트 설정
│   │       └── prompt_loader.py    # 프롬프트 로더
│   │
│   ├── utils/                       # 공통 유틸리티
│   │   ├── agent_config.py         # 에이전트 설정
│   │   └── prompt_loader.py        # 프롬프트 로더
│   │
│   ├── domain/                      # 도메인 모델 (DDD)
│   │   ├── common/                 # 공통 모델
│   │   ├── competency/             # 역량 도메인
│   │   ├── creator/                # 크리에이터 도메인
│   │   └── mission/                # 미션 도메인
│   │
│   ├── monitoring/                  # 모니터링
│   │   ├── langfuse.py             # Langfuse 통합
│   │   ├── prometheus_exporter.py  # Prometheus 메트릭
│   │   ├── performance_monitor.py  # 성능 모니터링
│   │   ├── metrics_collector.py    # 메트릭 수집
│   │   ├── tracing.py              # OpenTelemetry 트레이싱
│   │   └── logging_setup.py        # 구조화 로깅 (structlog)
│   │
│   ├── tasks/                       # Celery 태스크
│   │   ├── celery_app.py           # Celery 설정
│   │   ├── data_collection_tasks.py
│   │   ├── analytics_tasks.py
│   │   └── notification_tasks.py
│   │
│   ├── tools/                       # 에이전트 도구
│   │   ├── competency_tools.py     # CompetencyAnalyzer, SecurityTool
│   │   ├── llm_tools.py            # LLM 관련 도구
│   │   ├── vector_search_tools.py  # 벡터 검색 도구
│   │   └── vector_store_utils.py   # 벡터 스토어 유틸리티
│   │
│   ├── graphs/                      # LangGraph 워크플로우
│   │   └── main_orchestrator.py    # 메인 오케스트레이터
│   │
│   ├── config/                      # 설정
│   │   ├── constants.py            # 상수 정의
│   │   └── __init__.py
│   │
│   ├── app/                         # FastAPI 앱
│   │   ├── main.py                 # 앱 진입점
│   │   ├── dependencies.py         # 의존성 주입
│   │   └── lifespan.py             # 앱 생명주기
│   │
│   └── data/models/                 # 데이터 모델
│       ├── data_models.py          # 콘텐츠 메타데이터
│       ├── mission_models.py       # 미션 모델
│       ├── competency_models.py    # 역량 모델 (CompetencyQuestion, UserResponse)
│       ├── user_models.py          # 사용자 모델
│       ├── audit_models.py         # 감사 모델
│       └── creator_history_models.py # 크리에이터 이력 모델
│
├── config/
│   └── settings.py                 # Pydantic Settings (환경 설정)
│
├── node/                            # Node.js MCP Gateway
│   ├── src/
│   │   ├── server.ts               # Express 서버
│   │   ├── config/                 # 설정
│   │   │   └── index.ts
│   │   ├── agents/                 # Node.js 에이전트
│   │   │   ├── llmManagerAgent.ts
│   │   │   └── enterpriseBriefingAgent.ts
│   │   ├── graphs/                 # 오케스트레이터
│   │   │   └── mainOrchestrator.ts
│   │   ├── services/               # 서비스
│   │   │   ├── pythonApiClient.ts  # Python API 클라이언트
│   │   │   └── newsService.ts
│   │   ├── api/                    # API 라우트
│   │   │   ├── routes/
│   │   │   │   ├── agents.ts
│   │   │   │   └── data.ts
│   │   │   ├── middleware/
│   │   │   │   ├── auth.ts
│   │   │   │   ├── correlation.ts
│   │   │   │   └── security.ts
│   │   │   └── schemas/
│   │   │       ├── request.ts
│   │   │       ├── response.ts
│   │   │       └── common.ts
│   │   ├── types/                  # TypeScript 타입
│   │   │   ├── agentContracts.ts
│   │   │   └── creatorContracts.ts
│   │   ├── data/                   # 데이터
│   │   │   └── knowledge_packs.ts
│   │   └── scripts/                # 스크립트
│   │       └── prefetchNews.ts
│   └── package.json
│
├── frontend/                        # React 프론트엔드
│   ├── src/
│   │   ├── App.tsx                 # 앱 메인 컴포넌트
│   │   ├── main.tsx                # 앱 진입점
│   │   ├── api/                    # API 클라이언트
│   │   │   ├── client.ts           # Axios 클라이언트 (인증, MCP 포함)
│   │   │   └── types.ts            # TypeScript 타입
│   │   ├── components/             # UI 컴포넌트
│   │   │   ├── ui/                 # shadcn/ui 컴포넌트
│   │   │   ├── AppHeader.tsx
│   │   │   ├── CreatorEvaluationPanel.tsx
│   │   │   ├── MissionRecommendationPanel.tsx
│   │   │   ├── AnalyticsPanel.tsx
│   │   │   ├── AgentModelStatusPanel.tsx
│   │   │   └── EvaluationResultCard.tsx
│   │   ├── hooks/                  # 커스텀 훅
│   │   │   └── useHealthCheck.ts
│   │   ├── i18n/                   # 다국어 리소스
│   │   │   ├── config.ts
│   │   │   └── locales/
│   │   │       ├── ko.ts
│   │   │       └── en.ts
│   │   ├── lib/                    # 라이브러리 유틸
│   │   │   └── utils.ts
│   │   └── data/                   # 데이터
│   │       └── sampleMissions.ts
│   └── package.json
│
├── scripts/                         # 유틸리티 스크립트
│   ├── add_sample_documents.py
│   ├── performance_test.py
│   ├── test_api_connectivity.py
│   ├── test_gemini_direct.py
│   ├── test_sqlite_persistence.py
│   └── verify_config.py
│
├── tests/                           # 테스트
├── docker-compose.yml               # Docker 컨테이너 구성
├── Dockerfile                       # Docker 이미지 빌드
├── requirements.txt                 # Python 의존성
├── main.py                          # 레거시 진입점 (하위 호환)
└── .env.example                     # 환경변수 템플릿
```

## 설치 및 실행

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose (선택)

**로컬 시스템 의존성** (macOS):

```bash
# Tesseract OCR (이미지 텍스트 추출용)
brew install tesseract tesseract-lang

# PostgreSQL 클라이언트 (데이터베이스 연결용)
brew install postgresql
```

**로컬 시스템 의존성** (Ubuntu/Debian):

```bash
sudo apt-get update && sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-kor \
    tesseract-ocr-eng \
    libpq-dev
```

### 환경 변수 설정

```bash
cp .env.example .env
```

필수 환경 변수:

```env
# LLM API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
VOYAGE_API_KEY=pa-...

# LLM Model Names
ANTHROPIC_MODEL_NAME=claude-sonnet-4-5-20250929
OPENAI_MODEL_NAME=gpt-5.2
GEMINI_MODEL_NAME=gemini-2.5-flash

# LLM Routing (선택)
DEFAULT_LLM_MODEL=claude-sonnet-4-5-20250929
FAST_LLM_MODEL=gemini-2.5-flash
DEEP_LLM_MODEL=gpt-5.2
FALLBACK_LLM_MODEL=gemini-2.5-flash

# Embedding Configuration
DEFAULT_EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL_NAME=text-embedding-3-large
VOYAGE_EMBEDDING_MODEL_NAME=voyage-3
GEMINI_EMBEDDING_MODEL_NAME=text-embedding-004

# Vector DB (Pinecone)
VECTOR_DB_PROVIDER=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX_NAME=creator-onboarding
PINECONE_NAMESPACE=default

# MCP Configuration
SUPADATA_API_KEY=...

# MCP Tool Policy (Retry/Backoff/Circuit Breaker) - 운영 튜닝용 (선택)
# Web
MCP_WEB_FAIL_MAX=3
MCP_WEB_RESET_TIMEOUT_SECS=20
MCP_WEB_TIMEOUT_SECS=8
MCP_WEB_MAX_RETRIES=2
MCP_WEB_BACKOFF_BASE_SECS=0.4
MCP_WEB_BACKOFF_MAX_SECS=3.0
MCP_WEB_JITTER_SECS=0.2

# YouTube
MCP_YOUTUBE_FAIL_MAX=3
MCP_YOUTUBE_RESET_TIMEOUT_SECS=30
MCP_YOUTUBE_TIMEOUT_SECS=12
MCP_YOUTUBE_MAX_RETRIES=1
MCP_YOUTUBE_BACKOFF_BASE_SECS=0.6
MCP_YOUTUBE_BACKOFF_MAX_SECS=3.0
MCP_YOUTUBE_JITTER_SECS=0.2

# Supadata
MCP_SUPADATA_FAIL_MAX=4
MCP_SUPADATA_RESET_TIMEOUT_SECS=45
MCP_SUPADATA_TIMEOUT_SECS=20
MCP_SUPADATA_MAX_RETRIES=1
MCP_SUPADATA_BACKOFF_BASE_SECS=0.8
MCP_SUPADATA_BACKOFF_MAX_SECS=4.0
MCP_SUPADATA_JITTER_SECS=0.3

## MCP Tool Priority (optional)

`tool_enrichment` 단계에서 외부 도구(web/supadata/youtube)를 호출할 때, 비용/레이턴시 목적에 따라 호출 우선순위를 지정할 수 있습니다.

- **tool_priority=supadata_first**: 가능한 경우 `supadata`를 먼저 실행하고, 결과가 없으면 `web`을 fallback으로 실행합니다. (URL 기반 스크랩/크롤이 이미 존재하는 케이스에 유리)
- **tool_priority=parallel**: **속도 우선** 모드로 `web`과 `supadata`를 병렬 실행합니다. 오케스트레이터는 `cost_preference="speed"`일 때 기본으로 주입합니다.

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/ai_learning_db
REDIS_URL=redis://localhost:6379/0

# Authentication
SECRET_KEY=your-secret-key
ENABLE_AUTH=true

# RAG & Search Configuration
RERANKER_THRESHOLD=0.0
QUERY_EXPANSION_ENABLED=true

# Deep Agents (선택)
DEEPAGENT_MAX_STEPS=8
DEEPAGENT_CRITIC_ROUNDS=2
DEEPAGENT_TIMEOUT_SECS=60

# Cloud (Naver Cloud Platform, 선택)
CLOUD_PROVIDER=ncp
NCLOUD_ACCESS_KEY_ID=...
NCLOUD_SECRET_KEY=...

# Observability (선택)
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 로컬 개발

**Backend (Python)**

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn src.app.main:app --reload --port 8000
```

**Backend (Node.js)**

```bash
cd node
npm install
npm run dev
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

### Docker 실행

```bash
# 전체 서비스 실행
docker-compose up -d

# 모니터링 포함 실행
docker-compose --profile monitoring up -d

# 특정 서비스만 실행
docker-compose up -d api postgres redis

# 로그 확인
docker-compose logs -f api
```

**서비스 구성:**

| 서비스 | 포트 | 설명 |
|--------|------|------|
| api | 8000 | FastAPI 백엔드 |
| mcp-gateway | 3001 | Node.js MCP 서버 |
| postgres | 5432 | PostgreSQL 데이터베이스 |
| redis | 6379 | Redis 캐시/세션 |
| celery-worker | - | 백그라운드 작업 처리 |
| flower | 5555 | Celery 모니터링 (선택) |

## API 엔드포인트

### 크리에이터 평가

```http
POST /api/v1/creator/evaluate
Content-Type: application/json

{
  "platform": "instagram",
  "handle": "creator_handle",
  "profile_url": "https://instagram.com/creator_handle",
  "metrics": {
    "followers": 50000,
    "avg_likes": 2500,
    "avg_comments": 150
  }
}
```

**응답 예시:**

```json
{
  "success": true,
  "platform": "instagram",
  "handle": "creator_handle",
  "decision": "accept",
  "grade": "A",
  "score": 85.0,
  "score_breakdown": {
    "followers": 35.0,
    "engagement": 28.0,
    "frequency": 12.0,
    "brand_fit": 10.0
  },
  "tags": ["top_candidate", "has_similar_creators"],
  "risks": [],
  "report": "=== Creator Evaluation Report ===...",
  "rag_enhanced": {
    "similar_creators": [...],
    "category_insights": "...",
    "market_context": "..."
  }
}
```

### 역량 진단

```http
POST /api/v1/competency/diagnose
Content-Type: application/json

{
  "user_id": "user_123",
  "questions": [
    {"question_id": "q1", "question_text": "...", "domain": "education", "competency_area": "digital_literacy"}
  ],
  "responses": [
    {"question_id": "q1", "response_value": 4, "response_time": 15.5, "confidence_score": 0.8}
  ]
}
```

**응답 예시:**

```json
{
  "success": true,
  "analysis_result": {
    "competency_scores": {"digital_literacy": 0.75, "communication": 0.82},
    "strengths": ["communication"],
    "weaknesses": ["digital_literacy"],
    "learning_patterns": {"avg_response_time": 12.5, "response_pattern": "consistent"},
    "overall_level": "중급"
  },
  "recommendations": [
    {
      "type": "weakness_improvement",
      "competency_area": "digital_literacy",
      "priority": "high",
      "suggested_actions": ["디지털 리터러시 기초 과정 수강", "실습 프로젝트 참여"]
    }
  ]
}
```

### 미션 추천

```http
POST /api/v1/missions/recommend
Content-Type: application/json

{
  "creator_id": "creator_123",
  "creator_profile": {
    "followers": 50000,
    "engagement_rate": 4.5,
    "category": "lifestyle",
    "platform": "instagram"
  },
  "onboarding_result": {
    "grade": "A",
    "score": 85,
    "tags": ["top_candidate"]
  },
  "missions": [...],
  "filters": {
    "mission_types": ["sponsored_post"],
    "min_reward": 100000
  }
}
```

### RAG 쿼리 (SSE 스트리밍)

```http
GET /api/v1/rag/query/stream?query=역량진단&query_type=competency_assessment&user_id=user_123
Accept: text/event-stream
```

### MCP 검색

```http
POST /api/v1/mcp/hybrid-search
Content-Type: application/json

{
  "query": "패션 인플루언서 마케팅",
  "limit": 10,
  "filters": {"category": "fashion"},
  "vector_weight": 0.7
}
```

### 세션 관리

```http
# 세션 상태 조회
GET /api/v1/session/{session_id}

# 세션 복원 및 계속
POST /api/v1/session/{session_id}/resume
Content-Type: application/json
{"message": "이어서 분석해주세요"}

# 세션 삭제
DELETE /api/v1/session/{session_id}
```

### 헬스체크

```http
GET /health

{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "llm": "ok",
    "vector_db": "ok",
    "mcp": "ok",
    "database": "ok",
    "redis": "ok"
  }
}
```

## LLM 멀티 모델 전략

시스템은 작업 특성에 따라 최적의 LLM을 자동 선택합니다:

| 에이전트/작업 | 기본 모델 | 폴백 모델 |
|-------------|----------|----------|
| 일반 대화 | Claude Sonnet 4.5 | Gemini 2.5 Flash |
| 역량 진단 | Claude Sonnet 4.5 | GPT-5.2 |
| 추천 생성 | GPT-5.2 | Claude Sonnet 4.5 |
| 검색 요약 | Gemini 2.5 Flash | GPT-5.2 |
| 분석 리포트 | Claude Sonnet 4.5 | GPT-5.2 |
| 미션 매칭 | GPT-5.2 | Claude Sonnet 4.5 |
| RAG 응답 | GPT-5.2 | Claude Sonnet 4.5 |
| Deep Agents | Claude Sonnet 4.5 | GPT-5.2 |
| 크리에이터 평가 | Claude Sonnet 4.5 | Gemini 2.5 Flash |

### LLM 라우팅 로직

```python
# Cost/Latency 기반 자동 라우팅
{
  "cost_hint": "budget"  # → Gemini 2.5 Flash 선택
  "latency_hint": "fast"  # → Gemini 2.5 Flash 선택
  "task_type": "analysis"  # → Deep 모델 (GPT-5.2) 선택
}
```

## Embedding 전략

| 제공자 | 모델 | 용도 | 비고 |
|--------|------|------|------|
| **Voyage AI** | voyage-3 | 기본 임베딩 | 고품질, 다국어 지원 |
| OpenAI | text-embedding-3-large | 폴백 | 높은 정확도 |
| Google | text-embedding-004 | 비용 효율 | Gemini 연동 |
| SentenceTransformer | all-MiniLM-L6-v2 | 로컬 폴백 | 오프라인 지원 |

## 모니터링

### Prometheus 메트릭

- `agent_requests_total`: 에이전트 요청 수
- `agent_latency_seconds`: 응답 지연 시간
- `llm_tokens_used`: LLM 토큰 사용량
- `scraping_success_rate`: 스크래핑 성공률
- `rag_retrieval_latency`: RAG 검색 지연 시간
- `semantic_cache_hit_rate`: 시맨틱 캐시 히트율

### Langfuse 트레이싱

모든 LLM 호출은 Langfuse로 자동 트레이싱됩니다:
- 토큰 사용량 추적
- 응답 품질 분석
- 비용 모니터링
- RAG 파이프라인 성능 분석

### OpenTelemetry

분산 트레��싱 지원:
- FastAPI 요청 추적
- Redis/PostgreSQL 쿼리 추적
- 외부 HTTP 호출 추적

### Circuit Breaker

외부 서비스 장애 시 자동 차단 및 복구:

```http
GET /api/v1/circuit-breaker/status
POST /api/v1/circuit-breaker/reset/{name}
```

## 개발 가이드

### 새 에이전트 추가

1. `src/agents/` 디렉토리에 새 에이전트 모듈 생성
2. `BaseAgent` 클래스 상속
3. `execute()` 메서드 구현
4. `config/settings.py`의 `AGENT_MODEL_CONFIGS`에 등록
5. 오케스트레이터에 등록

```python
from src.core.base import BaseAgent, BaseState
from src.utils.agent_config import get_agent_runtime_config
from pydantic import Field
from typing import Optional, Dict, Any, List

class MyAgentState(BaseState):
    """에이전트 상태"""
    result: Optional[Dict[str, Any]] = None
    items: List[str] = Field(default_factory=list)

class MyAgent(BaseAgent[MyAgentState]):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        merged_config = get_agent_runtime_config("my_agent", config)
        super().__init__("MyAgent", merged_config)
        self.agent_model_config = merged_config

    async def execute(self, state: MyAgentState) -> MyAgentState:
        """에이전트 메인 실행 로직"""
        try:
            state = await self.pre_execute(state)

            # 에이전트 로직 구현
            result = await self._process(state)
            state.result = result

            state = await self.post_execute(state)
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            state.add_error(str(e))

        return state
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/

# 특정 에이전트 테스트
pytest tests/agents/test_creator_agent.py -v

# 커버리지 포함
pytest --cov=src tests/

# 비동기 테스트
pytest tests/ -v --asyncio-mode=auto
```

### 코드 스타일

```bash
# 포맷팅
black src/
isort src/

# 린팅
ruff check src/
mypy src/
```

## 트러블슈팅

### MCP 연결 실패

```bash
# MCP 서버 상태 확인
curl http://localhost:3001/health

# 로그 확인
docker-compose logs mcp-gateway

# Supadata API 키 확인
echo $SUPADATA_API_KEY
```

### LLM API 오류

1. API 키 확인: `.env` 파일의 키 유효성 검증
2. 레이트 리밋: 요청 간격 조절
3. 폴백 동작: 자동으로 대체 모델 사용
4. 재시도 설정: `retry.max_retries`, `retry.backoff_ms` 조정

### 벡터 DB 연결 문제

```bash
# Pinecone 상태 확인
echo $PINECONE_API_KEY
echo $PINECONE_INDEX_NAME

# 로컬 ChromaDB 사용 시
export VECTOR_DB_PROVIDER=chromadb
```

### 세션 상태 복원 실패

```bash
# SQLite 체크포인터 상태 확인
ls -la checkpoints.sqlite

# 세션 클리어
curl -X DELETE http://localhost:8000/api/v1/session/{session_id}
```

### 스크래핑 실패

- Instagram/TikTok 프로필이 비공개인 경우 메트릭 추출 불가
- 플랫폼별 제한 사항 확인
- Supadata API 키 유효성 확인

### ML 모델 로딩 실패

```bash
# scikit-learn/numpy 버전 확인
pip show scikit-learn numpy

# PyTorch 확인 (sentence-transformers용)
pip show torch
```

## 주요 의존성

| 패키지 | 버전 | 용도 |
|--------|------|------|
| langgraph | 0.2.x | AI 오케스트레이션 |
| langchain | 0.3.x | LLM 체인 |
| fastapi | 0.115.x | 웹 프레임워크 |
| pinecone | 5.x | 벡터 DB |
| voyageai | 0.3.x | 임베딩 |
| sentence-transformers | 3.3.x | 로컬 임베딩/Reranker |
| scikit-learn | 1.6.x | ML 모델 |
| celery | 5.4.x | 태스크 큐 |
| langfuse | 2.x | LLM 관측성 |

## 라이선스

MIT License

## 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
