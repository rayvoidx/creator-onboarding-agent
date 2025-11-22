## Node + TypeScript Service

This folder provides a production-ready Node.js + TypeScript service for the consumer-agent-system. It exposes an API to run agents and is optimized for non-blocking I/O and real-time use cases.

### Requirements
- Node.js 18+

### Setup
```bash
cd node
npm install
cp env.example .env # then edit values
npm run dev
```

Server runs on `http://localhost:3001` by default.

### API (BFF for Frontend)

#### Base Endpoint
- POST `/api/agents/run`
  - Common body shape:
    ```json
    { "agentType": "llmManager | enterpriseBriefing | creatorOnboarding | missionRecommend", "input": { ... }, "params": { ... } }
    ```
  - Optional header (if configured): `Authorization: Bearer <API_TOKEN>`
  - Common success envelope:
    ```json
    {
      "success": true,
      "data": {
        "id": "run_...",
        "output": { ... backend-specific payload ... },
        "usage": { "durationMs": 0, "model": "..." }
      },
      "timestamp": 1710000000000
    }
    ```
  - Error envelope:
    ```json
    {
      "success": false,
      "error": { "code": 400, "message": "Invalid request" },
      "timestamp": 1710000000000
    }
    ```

#### LLM Manager Agent
- Simple example:
  ```json
  { "agentType": "llmManager", "input": "Hello" }
  ```

#### Enterprise Briefing Agent
- Example request:
  ```bash
  curl -X POST http://localhost:3001/api/agents/run \
    -H "Content-Type: application/json" \
    -d '{
      "agentType": "enterpriseBriefing",
      "input": {"topic": "Q3 sales pipeline", "timeframe": "last_30d", "audience": "exec"}
    }'
  ```

#### Creator Onboarding (Python FastAPI 연동)
- `agentType: "creatorOnboarding"` 일 때 Node가 자동으로 Python 백엔드의 `/api/v1/creator/evaluate`를 호출합니다.
- Request example:
  ```bash
  curl -X POST http://localhost:3001/api/agents/run \
    -H "Content-Type: application/json" \
    -d '{
      "agentType": "creatorOnboarding",
      "input": {
        "platform": "tiktok",
        "handle": "sample_creator",
        "profile_url": "https://www.tiktok.com/@sample_creator",
        "metrics": {
          "followers": 250000,
          "avg_likes": 8000,
          "avg_comments": 300,
          "posts_30d": 20,
          "brand_fit": 0.7,
          "reports_90d": 0
        }
      }
    }'
  ```
- `data.output` 구조는 Python `CreatorEvaluationResponse` 와 동일합니다:
  - `platform`, `handle`, `decision`, `grade`, `score`, `score_breakdown`, `tags`, `risks`, `report`, `raw_profile`, `timestamp`

#### Mission Recommendation (Python FastAPI 연동)
- `agentType: "missionRecommend"` 일 때 Node가 `/api/v1/missions/recommend`를 호출합니다.
- Request example (온보딩 결과를 이용해 미션 추천):
  ```bash
  curl -X POST http://localhost:3001/api/agents/run \
    -H "Content-Type: application/json" \
    -d '{
      "agentType": "missionRecommend",
      "input": {
        "creator_id": "creator_1",
        "creator_profile": {
          "platform": "tiktok",
          "handle": "sample_creator",
          "onboarding_score": 87.5,
          "grade": "A"
        },
        "onboarding_result": {
          "grade": "A",
          "tags": ["top_candidate"],
          "risks": []
        },
        "missions": [
          {
            "id": "mission_1",
            "name": "테스트 캠페인 미션",
            "type": "content",
            "reward_type": "fixed",
            "reward_amount": 500000,
            "currency": "KRW",
            "requirement": {
              "min_followers": 0,
              "min_engagement_rate": 0.0,
              "min_posts_30d": 0,
              "min_grade": "C",
              "allowed_platforms": []
            },
            "metadata": {}
          }
        ],
        "filters": {
          "min_reward": 100000
        }
      }
    }'
  ```
- `data.output` 구조는 Python `MissionRecommendationResponse` 와 동일합니다:
  - `creator_id`, `recommendations` (각 항목은 `mission_id`, `mission_name`, `mission_type`, `reward_type`, `score`, `reasons`, `metadata`), `timestamp`

#### Backend URL / Auth
- Node → Python 백엔드 호출 기본 URL:
  - Docker compose 내부: `http://ai-learning-api:8000`
  - 로컬 개발 시 override: `.env` 에 `PY_BACKEND_URL=http://localhost:8000`
- Python 쪽에서 API 토큰을 사용하는 경우:
  - `.env` 에 `API_TOKEN=...` 을 설정하면 Node가 Python으로도 `Authorization: Bearer <API_TOKEN>` 헤더를 같이 전달합니다.

### Local Data Endpoints (No credentials required)
- `GET /api/data/news` — Read cached news items
- `POST /api/data/news/refresh` — Fetch RSS and refresh cache (uses public feeds)

```bash
curl http://localhost:3001/api/data/news
curl -X POST http://localhost:3001/api/data/news/refresh
```

To include local news in a briefing:

```bash
curl -X POST http://localhost:3001/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "agentType": "enterpriseBriefing",
    "input": {"topic": "Weekly ops status"},
    "params": {"sources": ["local:news"]}
  }'
```

### Offline/On-Prem Usage
- If network is unavailable, the agent falls back to built-in sample knowledge pack for context.
- You can prefetch news cache for demo environments:

```bash
npm run prefetch:news
```

### n8n Integration
- Use an HTTP Request Node:
  - Method: POST
  - URL: `http://agent-node:3001/api/agents/run` (inside compose) or `http://localhost:3001/api/agents/run`
  - JSON Body:
    ```json
    { "agentType": "enterpriseBriefing", "input": {"topic": "Ops status", "timeframe": "last_7d", "audience": "ops"} }
    ```
  - To use local news context:
    ```json
    { "agentType": "enterpriseBriefing", "input": {"topic": "Ops status"}, "params": {"sources": ["local:news"]} }
    ```

### Build & Run
```bash
npm run build
npm start
```

### Docker
```bash
docker build -t consumer-agent-node .
docker run -p 3001:3001 --env-file ./env.example consumer-agent-node
```


