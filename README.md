# Creator Onboarding Agent

AI 기반 크리에이터 온보딩 평가 시스템. LangGraph 오케스트레이션과 멀티 에이전트 아키텍처를 활용하여 SNS 크리에이터의 적합성을 자동으로 분석하고, 최적의 미션을 추천합니다.

## 주요 기능

- **크리에이터 평가**: Instagram/TikTok 프로필 자동 스크래핑 및 메트릭 추출
- **등급 산정**: S/A/B/C/D 등급과 세부 점수 (콘텐츠 품질, 참여도, 브랜드 적합성)
- **미션 추천**: 크리에이터 특성 기반 최적 미션 매칭
- **인사이트 리포트**: RAG 파이프라인을 통한 심층 분석
- **다국어 지원**: 한국어/영어 UI

## 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **AI Orchestration**: LangGraph, LangChain
- **LLM**: OpenAI GPT-5.1, Anthropic Claude Sonnet 4.5, Google Gemini (멀티 모델 플릿)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector DB**: ChromaDB
- **External Integration**: Supadata MCP (웹 스크래핑)

### Frontend
- **Framework**: React 18 + TypeScript
- **UI Library**: Material-UI (MUI)
- **State Management**: TanStack Query
- **i18n**: react-i18next
- **Build Tool**: Vite

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Monitoring**: Prometheus, Grafana
- **Tracing**: Langfuse (LLM observability)

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                        │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────┐         │
│  │ 평가 패널 │  │ 미션 추천 패널 │  │ 분석 리포트 패널 │         │
│  └────┬─────┘  └──────┬───────┘  └───────┬────────┘         │
└───────┼───────────────┼──────────────────┼──────────────────┘
        │               │                  │
        ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Gateway                           │
│  /api/evaluate  │  /api/recommend  │  /api/insights          │
└───────┬─────────────────┬──────────────────┬────────────────┘
        │                 │                  │
        ▼                 ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                 LangGraph Orchestrator                       │
│  ┌────────────────┐  ┌───────────────┐  ┌────────────────┐  │
│  │ CreatorAgent   │  │ MissionAgent  │  │ AnalyticsAgent │  │
│  │ (프로필 분석)   │  │ (미션 매칭)    │  │ (인사이트)      │  │
│  └───────┬────────┘  └───────┬───────┘  └───────┬────────┘  │
│          │                   │                  │            │
│  ┌───────┴───────────────────┴──────────────────┴───────┐   │
│  │              SearchAgent (RAG Pipeline)               │   │
│  │         ChromaDB + Hybrid Search + Reranking          │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────┐
│                    External Services                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Supadata MCP │  │ LLM Fleet    │  │ Langfuse         │   │
│  │ (스크래핑)    │  │ (GPT/Claude) │  │ (트레이싱)        │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 디렉토리 구조

```
creator-onboarding-agent/
├── src/
│   ├── agents/                    # AI 에이전트
│   │   ├── base.py               # 에이전트 베이스 클래스
│   │   ├── orchestrator.py       # LangGraph 오케스트레이터
│   │   ├── creator_onboarding_agent/  # 크리에이터 평가
│   │   ├── mission_agent/        # 미션 추천
│   │   ├── analytics_agent/      # 분석 리포트
│   │   ├── search_agent/         # RAG 검색
│   │   └── recommendation_agent/ # 개인화 추천
│   │
│   ├── app/                      # FastAPI 애플리케이션
│   │   ├── main.py              # 앱 엔트리포인트
│   │   └── routes/              # API 엔드포인트
│   │
│   ├── services/                 # 비즈니스 로직
│   │   ├── supadata_mcp.py      # MCP 스크래핑 서비스
│   │   └── rag_pipeline.py      # RAG 파이프라인
│   │
│   ├── tools/                    # LangChain 도구
│   │   └── llm_tools.py         # LLM 유틸리티
│   │
│   ├── mcp/                      # MCP 설정
│   │   └── mcp_config.json
│   │
│   └── monitoring/               # 모니터링
│       └── metrics.py
│
├── frontend/                     # React 프론트엔드
│   ├── src/
│   │   ├── api/                 # API 클라이언트
│   │   ├── components/          # UI 컴포넌트
│   │   ├── hooks/               # 커스텀 훅
│   │   └── i18n/                # 다국어 리소스
│   └── package.json
│
├── tests/                        # 테스트
├── docker-compose.yml            # 컨테이너 구성
├── requirements.txt              # Python 의존성
└── .env.example                  # 환경변수 템플릿
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

# MCP Configuration
SUPADATA_API_KEY=...

# Observability (Optional)
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### 로컬 개발

**Backend**

```bash
# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
uvicorn src.app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

**MCP Server** (웹 스크래핑용)

```bash
npx -y @anthropic-ai/supergateway --port 3001 \
  --stdio "npx -y supadata-mcp"
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
| mcp-gateway | 3001 | Node.js MCP 서버 (스크래핑) |
| postgres | 5432 | PostgreSQL 데이터베이스 |
| redis | 6379 | Redis 캐시 |
| celery-worker | - | 백그라운드 작업 처리 |
| flower | 5555 | Celery 모니터링 (선택) |

**Docker 이미지 빌드:**

```bash
# API 이미지만 빌드
docker build -t creator-onboarding-api .

# 모든 서비스 빌드
docker-compose build
```

**환경 변수:**

Docker 실행 시 `.env` 파일에서 환경 변수를 자동으로 로드합니다:

```bash
# .env 파일 생성
cp .env.example .env

# 필수 값 설정
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
SECRET_KEY=your-secret-key
```

## API 엔드포인트

### 크리에이터 평가

```http
POST /api/evaluate
Content-Type: application/json

{
  "platform": "instagram",
  "handle": "creator_handle",
  "profile_url": "https://instagram.com/creator_handle"
}
```

**응답 예시:**

```json
{
  "grade": "A",
  "total_score": 85,
  "scores": {
    "content_quality": 88,
    "engagement": 82,
    "brand_fit": 85
  },
  "decision": "APPROVED",
  "tags": ["lifestyle", "fashion", "high_engagement"],
  "risks": [],
  "report": "해당 크리에이터는 패션/라이프스타일 분야에서..."
}
```

### 미션 추천

```http
POST /api/recommend
Content-Type: application/json

{
  "creator": {
    "id": "creator_123",
    "followers": 50000,
    "engagement_rate": 4.5,
    "category": "lifestyle"
  },
  "missions": [...],
  "min_score": 70
}
```

### 인사이트 리포트

```http
POST /api/insights
Content-Type: application/json

{
  "report_type": "creator_analysis",
  "user_id": "user_123",
  "data": {...}
}
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
    "mcp": "ok"
  }
}
```

## 에이전트 상세

### CreatorOnboardingAgent

SNS 프로필을 분석하여 크리에이터의 온보딩 적합성을 평가합니다.

**주요 기능:**
- Supadata MCP를 통한 프로필 스크래핑
- 정규식 기반 메트릭 자동 추출 (팔로워, 게시물 수, 좋아요 등)
- LLM 기반 콘텐츠 품질 분석
- 등급 산정 및 리포트 생성

**추출 메트릭:**
- `followers`: 팔로워 수
- `following`: 팔로잉 수
- `posts_count`: 총 게시물 수
- `avg_likes`: 평균 좋아요
- `avg_comments`: 평균 댓글
- `bio`: 프로필 소개

### MissionAgent

크리에이터와 미션 간의 적합도를 계산하고 최적의 미션을 추천합니다.

**매칭 요소:**
- 카테고리 일치도
- 팔로워 수 vs 미션 요구사항
- 참여율 분석
- 과거 성과 데이터

### AnalyticsAgent

RAG 파이프라인을 활용하여 심층 인사이트 리포트를 생성합니다.

**리포트 유형:**
- 크리에이터 성과 분석
- 미션 효율성 분석
- 트렌드 인사이트

### SearchAgent

하이브리드 검색(키워드 + 시맨틱)과 리랭킹을 통해 관련 데이터를 검색합니다.

**검색 파이프라인:**
1. 키워드 검색 (BM25)
2. 시맨틱 검색 (임베딩)
3. 결과 융합 (RRF)
4. 리랭킹 (Cross-encoder)

## LLM 멀티 모델 전략

시스템은 작업 특성에 따라 최적의 LLM을 자동 선택합니다:

| 작업 | 기본 모델 | 폴백 모델 |
|------|----------|----------|
| 크리에이터 분석 | Claude Sonnet 4.5 | GPT-5.1 |
| 미션 추천 | GPT-5.1 | Claude Sonnet |
| 리포트 생성 | GPT-5.1 | Claude Sonnet |
| 임베딩 | text-embedding-3-small | - |

## 모니터링

### Prometheus 메트릭

- `agent_requests_total`: 에이전트 요청 수
- `agent_latency_seconds`: 응답 지연 시간
- `llm_tokens_used`: LLM 토큰 사용량
- `scraping_success_rate`: 스크래핑 성공률

### Langfuse 트레이싱

모든 LLM 호출은 Langfuse로 자동 트레이싱됩니다:
- 토큰 사용량 추적
- 응답 품질 분석
- 비용 모니터링

## 개발 가이드

### 새 에이전트 추가

1. `src/agents/` 디렉토리에 새 에이전트 모듈 생성
2. `BaseAgent` 클래스 상속
3. `execute()` 메서드 구현
4. 오케스트레이터에 등록

```python
from agents.base import BaseAgent

class NewAgent(BaseAgent):
    async def execute(self, input_data: dict) -> dict:
        # 에이전트 로직 구현
        result = await self.llm.ainvoke(prompt)
        return {"output": result}
```

### 테스트 실행

```bash
# 전체 테스트
pytest tests/

# 특정 에이전트 테스트
pytest tests/agents/test_creator_agent.py -v
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
```

### LLM API 오류

1. API 키 확인: `.env` 파일의 키 유효성 검증
2. 레이트 리밋: 요청 간격 조절
3. 폴백 동작: 자동으로 대체 모델 사용

### 스크래핑 실패

- Instagram 프로필이 비공개인 경우 메트릭 추출 불가
- 플랫폼별 제한 사항 확인

## 라이선스

MIT License

## 기여

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
