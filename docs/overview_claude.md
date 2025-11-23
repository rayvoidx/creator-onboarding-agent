# Creator Onboarding Agent 시스템 개요

## 시스템 목적
크리에이터(TikTok, Instagram 등) 온보딩 자동화를 위한 **멀티에이전트 AI 시스템**입니다. LangGraph 기반 Python 백엔드(FastAPI)와 TypeScript/Node.js 에이전트로 구성된 하이브리드 아키텍처입니다.

## 핵심 기능

### 1. 크리에이터 온보딩 평가 (CreatorOnboardingAgent)
- **입력**: 플랫폼, 핸들, 프로필 URL, 메트릭스(팔로워, 좋아요, 댓글 등)
- **처리**: 휴리스틱 스코어링 + 규칙 기반 리스크 분석
- **출력**: 등급(S/A/B/C), 결정(accept/reject/hold), 점수(0-100), 리스크 태그

### 2. RAG 기반 지능형 질의응답
- 하이브리드 검색: ChromaDB 벡터 검색 + BM25 키워드 검색
- 문서 재순위화: CrossEncoder 기반
- 스트리밍 응답 지원 (SSE)

### 3. LangGraph 오케스트레이터
- 요청 라우팅: 의도 분석 후 적절한 워크플로우로 자동 분기
- 워크플로우 종류:
  - **competency**: 역량 진단
  - **recommendation**: 맞춤형 추천
  - **search**: 벡터 검색
  - **analytics**: 분석 리포트
  - **data_collection**: 데이터 수집
  - **deep_agents**: 계획-실행-비평 패턴의 고급 추론

### 4. 보조 에이전트들
- **CompetencyAgent**: 역량 진단 및 평가
- **RecommendationAgent**: 개인화된 학습자료 추천
- **SearchAgent**: 벡터 기반 지식 검색
- **AnalyticsAgent**: 분석 및 리포트 생성
- **LLMManagerAgent**: 모델 라우팅 및 관리
- **DataCollectionAgent**: 외부 데이터 수집

## 아키텍처 구조

```
Client → Python API (8000) → LangGraph Orchestrator → 에이전트들
                                    ↓
                              RAG Pipeline
                                    ↓
        PostgreSQL / Redis / ChromaDB / OpenAI API

Client → Node.js API (3001) → Enterprise Briefing Agent
```

## API 엔드포인트

### 크리에이터 온보딩
- `POST /api/v1/creator/evaluate`: 크리에이터 자동 평가

### RAG
- `POST /api/v1/rag/query`: RAG 기반 질의응답
- `GET /api/v1/rag/query/stream`: SSE 스트리밍

### 기타
- `POST /api/v1/competency/assess`: 역량진단
- `POST /api/v1/recommendations/generate`: 추천 생성
- `POST /api/v1/search/vector`: 벡터 검색
- `POST /api/v1/analytics/report`: 분석 리포트

## 주요 기술 스택
- **백엔드**: FastAPI, LangGraph, LangChain
- **데이터베이스**: PostgreSQL, Redis, ChromaDB
- **LLM**: OpenAI (gpt-5.1), Anthropic (옵션), Google Gemini (멀티 모델 플릿)
- **모니터링**: Langfuse, Prometheus
- **Node.js**: Express, TypeScript

---

# 핵심 지표 정의 (초안)

## 1. 온보딩 평가 지표

| 지표명 | 설명 | 측정 방법 |
|--------|------|-----------|
| **평가-라벨 일치도** | 시스템 결정(accept/reject/hold)과 실제 성과의 일치율 | (일치 건수 / 전체 평가 건수) × 100 |
| **등급 정확도** | 부여된 등급(S/A/B/C)과 실제 크리에이터 성과의 상관관계 | 등급별 평균 성과 지표 비교 |
| **처리 시간** | 평가 요청부터 결과 반환까지 소요 시간 | 평균 응답 시간 (ms) |

## 2. 미션 지표

| 지표명 | 설명 | 측정 방법 |
|--------|------|-----------|
| **미션 클릭률 (CTR)** | 추천된 미션에 대한 크리에이터의 클릭 비율 | (클릭 수 / 노출 수) × 100 |
| **미션 완수율** | 시작된 미션 중 완료된 비율 | (완수 건수 / 시작 건수) × 100 |
| **미션-크리에이터 적합도** | 추천된 미션과 크리에이터 프로필의 매칭 점수 | 추천 알고리즘 confidence score |

## 3. 보상 지표

| 지표명 | 설명 | 측정 방법 |
|--------|------|-----------|
| **보상 정확도** | 규칙 기반 보상 계산의 오류율 | (정확 계산 건수 / 전체 건수) × 100 |
| **보상 적시성** | 미션 완료 후 보상 지급까지 소요 시간 | 평균 지급 소요 시간 (hours) |
| **보상 만족도** | 크리에이터의 보상 체계에 대한 만족 점수 | NPS 또는 설문 점수 |

## 4. 인사이트 지표

| 지표명 | 설명 | 측정 방법 |
|--------|------|-----------|
| **RAG 응답 관련성** | 검색된 문서와 질문의 관련성 점수 | Retrieval relevance score (0-1) |
| **인사이트 활용률** | 생성된 인사이트가 실제 의사결정에 활용된 비율 | 활용 건수 / 생성 건수 |
| **리포트 생성 품질** | 분석 리포트의 정확성 및 유용성 | 사용자 피드백 점수 (1-5) |

---

## 다음 단계 제안

1. **데이터 수집 파이프라인 구축**: 위 지표 측정을 위한 로깅 체계
2. **평가 데이터셋 구축**: 골든 데이터셋(eval/golden.jsonl) 확장
3. **A/B 테스트 프레임워크**: 모델/알고리즘 개선 효과 측정
4. **대시보드 구축**: Grafana/Langfuse를 통한 실시간 모니터링