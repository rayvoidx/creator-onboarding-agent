<p align="center">
  <img src="docs/assets/hero-banner.svg" alt="Creator Onboarding Agent" width="840"/>
</p>

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

<p align="center">
  <img src="docs/assets/architecture.svg" alt="Architecture Diagram" width="840"/>
</p>

---

## 크리에이터 평가 시스템

### 개요

크리에이터 평가는 이 프로젝트의 핵심 기능입니다. SNS 핸들만 입력하면 프로필을 자동 스크래핑하고, 다층 스코어링 → 등급 산정 → 온보딩 결정을 수행합니다.

<p align="center">
  <img src="docs/assets/evaluation-pipeline.svg" alt="Evaluation Pipeline" width="840"/>
</p>

### 데이터 수집 전략

Instagram `og:description` 메타 태그에서 **100% 정확한** 팔로워/팔로잉/게시물 데이터를 추출합니다.

| 데이터 | 수집 방법 | 신뢰도 |
|--------|-----------|--------|
| 팔로워 수 | `og:description` 파싱 | `verified` — 프로필에서 직접 수집 |
| 팔로잉 수 | `og:description` 파싱 | `verified` |
| 총 게시물 수 | `og:description` 파싱 | `verified` |
| 디스플레이 네임 | `og:title` 파싱 | `verified` |
| 참여율 (좋아요/댓글) | 업계 평균 벤치마크 적용 | `estimated` — 비로그인 환경에서 접근 불가 |
| 게시 빈도 (posts/30d) | 총 게시물 기반 추정 | `estimated` |
| 바이오 텍스트 | JSON 구조 파싱 | `verified` (가용 시) |

**스크래핑 체인**: Supadata MCP (우선) → HttpMCP (폴백) → og:description → JSON 패턴 → 일반 정규식

```
og:description 예시:
"90K Followers, 3,368 Following, 558 Posts - Dem Jointz (@demjointz)..."
     ↓ 파싱
followers: 90,000 [verified]
following: 3,368  [verified]
total_posts: 558  [verified]
```

### 스코어링 시스템

#### 5개 평가 카테고리

각 카테고리는 독립적으로 0~max 범위에서 채점되며, 가중치 합계는 정확히 **1.0**으로 정규화됩니다.

| 카테고리 | 가중치 | 만점 | 평가 기준 | 데이터 소스 |
|----------|--------|------|-----------|------------|
| **followers** | 0.35 | 35점 | 7단계 티어 기반 (Mega~Rising) | verified |
| **engagement** | 0.25 | 25점 | 플랫폼별 벤치마크 대비 참여율 | estimated |
| **activity** | 0.15 | 15점 | 게시 빈도 (0.5회/일 = 만점) | estimated |
| **ff_ratio** | 0.10 | 10점 | 팔로잉/팔로워 비율 건강도 | verified |
| **brand_fit** | 0.15 | 15점 | 외부 입력 브랜드 적합도 | 외부 입력 |

가중치는 `config/settings.py`에서 환경변수로 조정 가능하며, 런타임에 합계 1.0으로 자동 정규화됩니다.

<p align="center">
  <img src="docs/assets/scoring-gauge.svg" alt="Scoring System" width="840"/>
</p>

```python
# config/settings.py
CREATOR_WEIGHT_FOLLOWERS = 0.35  # env: CREATOR_WEIGHT_FOLLOWERS
CREATOR_WEIGHT_ENGAGEMENT = 0.25
CREATOR_WEIGHT_ACTIVITY = 0.15
CREATOR_WEIGHT_FF_RATIO = 0.10
CREATOR_WEIGHT_BRAND_FIT = 0.15
# → 합계 = 1.0 (자동 정규화)
```

#### 팔로워 티어 분류

로그 스케일 기반의 7단계 인플루언서 티어:

| 티어 | 팔로워 범위 | 점수 (35점 기준) | 시장 가치 |
|------|------------|-----------------|-----------|
| **Mega** | 1M+ | 35.0 / 35 | 광고 단가 최고 |
| **Macro-Mega** | 500K+ | 32.4 / 35 | 대형 캠페인 |
| **Macro** | 100K+ | 28.9 / 35 | 브랜드 앰배서더 |
| **Mid-Tier** | 50K+ | 24.5 / 35 | 타겟 마케팅 |
| **Micro** | 10K+ | 19.3 / 35 | 니치 마케팅 |
| **Nano** | 1K+ | 12.3 / 35 | 커뮤니티 |
| **Rising** | <1K | 0~7.0 / 35 | 성장 잠재력 |

#### 참여율 (Engagement) 벤치마크

플랫폼별 업계 평균 참여율을 기준으로 정규화합니다:

| 플랫폼 | 벤치마크 참여율 | 채점 방식 |
|--------|----------------|-----------|
| Instagram | 1.8% | 벤치마크 대비 비율 (1.8% → 50%, 3.6% → 100%) |
| TikTok | 4.5% | 벤치마크 대비 비율 |
| YouTube | 2.5% | 벤치마크 대비 비율 |

> **참고**: 비로그인 환경에서는 개별 게시물 좋아요/댓글 수를 수집할 수 없어 업계 평균으로 추정합니다. 이는 `[estimated]` 라벨로 명시됩니다.

#### FF Ratio (팔로잉/팔로워 비율)

계정 건강도를 나타내는 핵심 지표:

| FF Ratio | 건강도 | 점수 비율 | 의미 |
|----------|--------|-----------|------|
| ≤ 0.05 | healthy | 100% | 셀러브리티 수준 (팔로잉 매우 적음) |
| ≤ 0.15 | healthy | 80% | 건강한 인플루언서 |
| ≤ 0.50 | moderate | 50% | 일반적 수준 |
| ≤ 1.00 | moderate | 20% | 팔로잉 다소 많음 |
| > 1.00 | unhealthy | 0% | 팔로우백 패턴 의심 |

#### 리스크 감점

확인된 데이터에 대해서만 감점이 적용됩니다 (추정 데이터로는 감점하지 않음):

| 리스크 | 감점 | 조건 |
|--------|------|------|
| `high_reports` | -15점 | 90일 내 신고 3건 이상 |
| `low_engagement` | -10점 | 참여율 0.2% 미만 (verified 데이터만) |
| `low_activity` | -5점 | 월 4회 미만 게시 (verified 데이터만) |
| `follow_back_pattern` | -5점 | FF ratio 1.5 초과 |

### 등급 체계

6단계 등급 시스템 (환경변수로 임계값 조정 가능):

| 등급 | 점수 범위 | 결정 | 설명 |
|------|-----------|------|------|
| **S** | 85+ | accept | 최우수 — 즉시 온보딩 |
| **A** | 70+ | accept | 우수 — 적극 추천 |
| **B** | 55+ | accept | 양호 — 추천 |
| **C** | 40+ | accept | 보통 — 조건부 추천 |
| **D** | 30+ | reject | 미흡 — 부적합 |
| **F** | <30 | reject | 부적합 — 데이터 부족 포함 |

```python
# config/settings.py — 등급 임계값 (환경변수로 조정 가능)
CREATOR_GRADE_S_THRESHOLD = 85
CREATOR_GRADE_A_THRESHOLD = 70
CREATOR_GRADE_B_THRESHOLD = 55
CREATOR_GRADE_C_THRESHOLD = 40
CREATOR_GRADE_D_THRESHOLD = 30
CREATOR_REJECT_THRESHOLD = 40
```

> **D/F 등급 추가 배경**: 이전에는 S/A/B/C 4단계만 존재하여 TikTok 스크래핑 실패(0점) 시에도 "C등급"으로 표시되는 문제가 있었습니다. D/F 등급을 추가하여 데이터 수집 실패 케이스를 정확히 반영합니다.

### API 응답 구조

`POST /api/v1/creator/evaluate` 응답의 핵심 필드:

```jsonc
{
  "success": true,
  "platform": "instagram",
  "handle": "demjointz",
  "display_name": "Dem Jointz",          // og:title에서 추출
  "decision": "accept",
  "grade": "B",
  "score": 62.0,

  // 티어 정보
  "tier": {
    "name": "Mid-Tier (50K+)",
    "followers": 90000,
    "following": 3368,
    "total_posts": 558,
    "ff_ratio": 0.037,
    "ff_health": "healthy",
    "display_name": "Dem Jointz"
  },

  // 구조화된 점수 상세 (각 항목에 기준 설명 + 데이터 출처)
  "score_breakdown": {
    "followers": {
      "score": 24.5,
      "max": 35.0,
      "description": "Mid-Tier (50K+) — 팔로워 90,000명",
      "source": "verified"
    },
    "engagement": {
      "score": 12.5,
      "max": 25.0,
      "description": "참여율 1.80% (업계 평균 추정)",
      "source": "estimated"
    },
    "activity": {
      "score": 15.0,
      "max": 15.0,
      "description": "게시 빈도 0.5회/일 (추정 15회/30일)",
      "source": "estimated"
    },
    "ff_ratio": {
      "score": 10.0,
      "max": 10.0,
      "description": "FF비율 0.037 (healthy)",
      "source": "verified"
    },
    "brand_fit": {
      "score": 0.0,
      "max": 15.0,
      "description": "브랜드 적합도 (미입력)",
      "source": "unavailable"
    }
  },

  // 필드별 데이터 신뢰도
  "data_confidence": {
    "followers": "verified",
    "following": "verified",
    "total_posts": "verified",
    "engagement": "estimated",
    "activity": "estimated"
  },

  "tags": [],
  "risks": [],
  "report": "...",              // 텍스트 리포트 (전체 분석 결과)
  "raw_profile": { ... },       // 스크래핑 원본 데이터
  "rag_enhanced": { ... },      // RAG 유사 크리에이터 분석 (nullable)
  "trend": { ... },             // 성장 트렌드 (2회 이상 평가 시, nullable)
  "timestamp": "2026-02-19T07:50:57.668609"
}
```

### 프론트엔드 시각화

`EvaluationResultCard` 컴포넌트에서 제공하는 시각화:

| 요소 | 설명 |
|------|------|
| **등급 게이지** | S~F 등급 스케일 위에 현재 점수 위치 표시 (컬러 코딩) |
| **티어 정보 카드** | 팔로워/팔로잉/게시물/FF비율을 그리드로 표시 + ff_health 뱃지 |
| **점수 바 차트** | 각 카테고리별 `score/max` 프로그레스 바 + 기준 설명 텍스트 |
| **신뢰도 뱃지** | `verified` (초록 체크), `estimated` (노란 물결), `unavailable` (회색 자물쇠) + 툴팁 |
| **성장 트렌드** | 이전 평가 대비 팔로워 변화량 + 추세 아이콘 (2회 이상 평가 시) |
| **리스크/태그 칩** | 위험 요소와 분류 태그를 색상 칩으로 표시 |
| **텍스트 리포트** | 모노스페이스 서식의 전체 분석 리포트 |

### 테스트 결과 예시

| 크리에이터 | 플랫폼 | 팔로워 | 등급 | 점수 | 결정 | 비고 |
|-----------|--------|--------|------|------|------|------|
| @demjointz | Instagram | 90K | B | 62.0 | accept | Mid-Tier, brand_fit 미입력(-15점) |
| @natgeo | Instagram | 275M | A | 72.5 | accept | Mega 티어, 최대 팔로워 점수 |
| @khaby.lame | TikTok | 0 | F | 0.0 | reject | TikTok JS 렌더링 필요 → 스크래핑 실패 |

### 설정 외부화 (config/settings.py)

모든 스코어링 상수는 환경변수로 조정 가능합니다:

```bash
# 등급 임계값
CREATOR_GRADE_S_THRESHOLD=85
CREATOR_GRADE_A_THRESHOLD=70
CREATOR_GRADE_B_THRESHOLD=55
CREATOR_GRADE_C_THRESHOLD=40
CREATOR_GRADE_D_THRESHOLD=30
CREATOR_REJECT_THRESHOLD=40

# 카테고리 가중치 (합계 자동 정규화)
CREATOR_WEIGHT_FOLLOWERS=0.35
CREATOR_WEIGHT_ENGAGEMENT=0.25
CREATOR_WEIGHT_ACTIVITY=0.15
CREATOR_WEIGHT_FF_RATIO=0.10
CREATOR_WEIGHT_BRAND_FIT=0.15

# 플랫폼별 참여율 벤치마크
CREATOR_ENGAGEMENT_RATE_IG=0.018
CREATOR_ENGAGEMENT_RATE_TT=0.045
CREATOR_ENGAGEMENT_RATE_YT=0.025
```

### 변경 파일 요약

| 파일 | 변경 내용 |
|------|-----------|
| `config/settings.py` | 17개 스코어링 상수 외부화 |
| `src/agents/creator_onboarding_agent/__init__.py` | 스코어링 리팩터링, 가중치 정규화, D/F 등급, 구조화된 score_breakdown, 트렌드 연동 |
| `src/api/schemas/response_schemas.py` | `ScoreDetail`, `TierInfo` 모델 추가, `CreatorEvaluationResponse` 확장 |
| `src/api/v1/routes/creator.py` | `rag_enhanced`, `tier`, `data_confidence`, `display_name`, `trend` 응답 포함 |
| `src/rag/prompt_templates.py` | `CREATOR_EVALUATION` PromptType 추가 |
| `src/rag/rag_pipeline.py` | `CREATOR_EVALUATION → creator_expert` 매핑 연결 |
| `frontend/src/api/types.ts` | `ScoreDetail`, `TierInfo` 인터페이스 추가 |
| `frontend/src/components/EvaluationResultCard.tsx` | 등급 게이지, 점수 바, 신뢰도 뱃지, 티어 카드, 트렌드 표시 |
| `frontend/src/i18n/locales/ko.ts` | 평가 UI 한국어 번역 추가 |
| `frontend/src/i18n/locales/en.ts` | 평가 UI 영문 번역 추가 |

### 해결된 이슈

| 이슈 | 이전 | 이후 |
|------|------|------|
| **가중치 합계 버그** | 0.40+0.30+0.15+0.10+0.15 = **1.10** (brand_fit 소실) | 합계 자동 정규화 → 정확히 **1.0** |
| **0점 = C등급** | S/A/B/C 4단계만 존재 → 0점도 "C" | D/F 추가 → 0점 = "F" + `data_insufficient` 태그 |
| **점수 기준 불투명** | `score_breakdown: {followers: 28.0}` (숫자만) | `{score: 24.5, max: 35.0, description: "...", source: "verified"}` |
| **RAG 결과 누락** | `rag_enhanced` 계산 후 API 응답에서 제외 | 응답에 포함 (nullable) |
| **데이터 신뢰도 미구분** | 추정/실제 구분 없음 | `data_confidence` 맵 + UI 뱃지 (verified/estimated/unavailable) |
| **트렌드 미반영** | `CreatorHistory` 존재하나 미사용 | 2회 이상 평가 시 성장 트렌드 리포트에 표시 |

---

## 주요 기능

| 기능 | 설명 | 에이전트 패턴 |
|------|------|-------------|
| **크리에이터 평가** | SNS 프로필 스크래핑, 메트릭 추출, S/A/B/C/D/F 등급 | RAG-enhanced + Heuristic |
| **미션 추천** | 크리에이터-미션 매칭, 적합도 점수 | Rule-based + LLM Hybrid |
| **역량 진단** | ML(RandomForest) 기반 역량 분석, 학습 추천 | ML + LLM + Security |
| **심층 추론** | 다단계 추론, Self-Critique 품질 향상 | CodeAct + ReAct |
| **RAG 검색** | 하이브리드 검색 → Reranking → SSE 스트리밍 | Compound AI System |
| **데이터 수집** | NILE/MOHW/KICCE API + YouTube/MCP | Tool-augmented Agent |

## 기술 스택

<p align="center">
  <img src="docs/assets/tech-stack.svg" alt="Tech Stack" width="840"/>
</p>

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
├── config/settings.py       # Pydantic Settings (scoring 상수 포함)
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
