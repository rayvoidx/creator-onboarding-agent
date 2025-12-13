## 서비스 · 모니터링 · 태스크 · 테스트 3차 코드리뷰 & 학습 노트

이 문서는 앞선 1·2차 코드리뷰에서 다루지 못한 **서비스 계층, 모니터링, Celery 태스크, 미들웨어, 테스트 코드**를 중심으로  
“운영 품질/안정성 관점”에서 더 깊게 분석하고, 에이전트 개발자가 배울 수 있는 패턴과 개선 포인트를 정리한 자료입니다.

대상 영역:
- `src/services/*`
- `src/tasks/*`
- `src/monitoring/*`
- `src/core/circuit_breaker.py`, `src/core/exceptions.py`
- `src/api/middleware/*` (특히 rate limit / correlation)
- `tests/*` (e2e, integration, unit)

각 섹션마다 **핵심 코드 블록 단위로 설계 의도, 장점, 문제, 개선 제안**을 기술합니다.

---

## 1. A/B 테스트, 감사, 인증 서비스 (`src/services`)

### 1.1. `src/services/ab_testing/service.py` – ABTestingService

#### 1.1.1. 도메인 모델 정의 (L20–L96)

- `ExperimentStatus`, `VariantType`, `PromptVariant`, `Experiment`, `ExperimentResult` 가 Pydantic 모델/Enum 으로 정의되어 있습니다.
- **의도**
  - 프롬프트 A/B 테스트를 위한 **실험/변형/결과**를 명확한 타입으로 표현해, 나중에 파일 저장/DB/외부 리포팅으로 확장하기 쉽게 합니다.
- **좋은 점**
  - `Experiment` 에 `target_prompt_type`, `primary_metric`, `user_percentage` 등을 담아서,  
    “어떤 프롬프트 타입에 어떤 실험이 적용되는지”를 코드만 보고도 이해할 수 있습니다.
- **개선 포인트**
  - 현재는 전부 **인메모리 딕셔너리/리스트**에 저장되고 있어, 프로세스 재시작 시 실험/결과가 날아갑니다.
    - 향후에는 SQLAlchemy 모델과 연결해 **영속 저장소(예: Postgres)** 로 옮길 수 있는 여지를 남겨두는 게 좋습니다.

#### 1.1.2. 실험 생성/시작/중지 (L109–L181)

- `create_experiment`:
  - 변형 리스트를 받아 `PromptVariant` 리스트로 만들고, 가중치를 정규화합니다.
  - `variants[i].weight` 의 합이 1이 되도록 정규화하는 부분이 명시적입니다.
- `start_experiment` / `stop_experiment`:
  - 상태를 `RUNNING`/`COMPLETED` 로 변경하고 `start_date`/`end_date` 를 설정합니다.
- **장점**
  - A/B 테스트 라이프사이클을 단일 서비스에서 관리하므로, API나 관리자 UI에서 이 레이어만 호출하면 됩니다.
- **개선 포인트**
  - `create_experiment` 에서 `user_percentage`, `primary_metric` 에 대한 **값 검증**이 거의 없습니다.
    - `user_percentage` 가 0~100 범위인지, `primary_metric` 이 미리 정의된 지표 중 하나인지 검증하는 것이 안전합니다.

#### 1.1.3. 사용자 할당/결과기록/통계 (L183–L357)

- `get_variant_for_user`:
  - 해시 기반으로 **사용자를 실험에 포함할지/어떤 변형을 줄지**를 결정합니다.
  - `user_percentage` 비율로 실험 대상자를 조절하며, 한 번 정해진 변형은 `_user_assignments` 에 캐시해 일관성을 유지합니다.
- `record_result`:
  - 실험 ID/변형 ID/응답시간/토큰수/품질 점수 등을 `ExperimentResult` 로 저장.
- `get_experiment_stats`:
  - 변형별 success rate, avg response time, avg quality/user feedback 등을 계산하고, 간단한 기준으로 winner를 선정합니다.
- **Good**
  - 실험 설계에서 가장 중요한 **랜덤 할당/결과 기록/기본 통계**가 한 서비스에 잘 모여 있습니다.
- **비판/개선**
  - 통계적 유의성 검증은 `sample_size >= 30` 만 보고 가장 높은 평균을 winner로 정하는 매우 단순한 방식입니다.
    - 실제 A/B 테스트에서는 **p-value, Bayesian AB, 최소 검출 효과(MDE)** 등을 고려해야 하므로, 향후 확장 공간으로 남겨 두는 것이 좋습니다.
  - `_user_assignments`, `_experiments`, `_results` 가 전부 인메모리라, **다중 프로세스/다중 인스턴스 환경에서 일관성이 깨질 수 있습니다.**

#### 1.1.4. 프롬프트와 실험 결합 (L375–L400)

- `get_prompt_with_experiment(user_id, prompt_type, default_prompt)`:
  - 사용자가 실험 대상이면, 해당 변형의 `content` 를 반환하고, 아니면 기본 프롬프트를 그대로 리턴합니다.
- **의도**
  - 에이전트/프롬프트 생성 코드에서 **한 줄로 A/B 테스트를 적용**할 수 있게 해줍니다.
- **개선 포인트**
  - 현재는 “첫 번째 활성 실험만 사용”하는데, 복수 실험이 있을 때의 정책이 없는 점을 주의해야 합니다.

---

### 1.2. `src/services/audit/service.py` – AuditService

#### 1.2.1. Dual-backend 설계 (메모리 vs DB) (L67–L83, L84–L104)

- `__init__` 에서 DB URL이 sqlite면 메모리 모드, 그 외에는 Postgres를 사용하려는 구조입니다.
- `initialize()`:
  - Postgres URL이면 동기 `create_engine` 로 테이블 생성 → 실패하면 메모리 모드로 폴백.
- **좋은 점**
  - 개발/테스트에서는 메모리 모드로 가볍게 사용하고, 운영에서는 DB에 남기는 유연성이 있습니다.
- **비판/개선**
  - `create_engine(sync_url)` 로 매번 새 엔진/세션을 만드는 구조(특히 `_persist_log`, `_query_database`)는 **성능/리소스 관점에서 비효율적**입니다.
    - 개선: 엔진/세션팩토리를 인스턴스 생성 시 한 번만 만들고 재사용하도록 리팩터링하는 것이 좋습니다.

#### 1.2.2. `log()` / `_persist_log()` / `query()` (L105–L220)

- `log()`:
  - `AuditLog` Pydantic 모델을 생성 후, 메모리 또는 DB에 기록.
  - 심각도에 따라 로그 레벨을 다르게 찍습니다.
- `_persist_log()`:
  - SQLAlchemy `AuditLogTable` 로 매핑하여 DB에 INSERT.
- `query()`:
  - 메모리/DB 중 어떤 백엔드를 쓰는지에 따라 `_query_memory` 또는 `_query_database` 호출.
- **좋은 점**
  - 같은 인터페이스로 메모리/DB를 모두 지원해, 상위 레이어는 백엔드 종류를 신경 쓸 필요가 없습니다.
- **개선 포인트**
  - 동기 DB 코드를 비동기 컨텍스트(예: FastAPI 핸들러/에이전트 실행 중)에서 쓰면, **이벤트 루프가 블로킹**될 수 있습니다.
    - 개선: audit은 비동기 큐/작업으로 넘기거나, 별도의 쓰레드 풀로 실행하는 것이 이상적입니다.

#### 1.2.3. 통계 계산 `get_stats()` (L343–L385)

- **역할**
  - 특정 기간의 감사 로그에 대해 액션별/심각도별/사용자별 카운트와 성공/실패 카운트/성공률을 계산합니다.
- **학습 포인트**
  - “로깅/감사 데이터로부터 간단한 운영 메트릭을 만드는 패턴”을 보여줍니다.

---

### 1.3. `src/services/auth/service.py` – AuthService

#### 1.3.1. 인메모리 사용자 저장소 (L37–L52, L76–L108)

- 사용자 생성/조회/인증이 모두 인메모리 딕셔너리 기반으로 이뤄집니다.
- **의도**
  - 이 프로젝트에서는 인증/인가가 **샘플/레퍼런스 수준**으로만 필요하기 때문에, 실제 DB 스키마/마이그레이션 없이 동작 가능하게 하기 위함입니다.
- **비판/개선**
  - 운영 환경에서는 반드시 **DB 백엔드 + 비밀번호 정책 + 계정 잠금 정책** 등이 필요합니다.
  - `_users`, `_users_by_email` 등이 모두 메모리이므로, 워커 리스타트/스케일 아웃 시 계정이 사라집니다.

#### 1.3.2. JWT 토큰 생성/검증 (L134–L185, L186–L213)

- `create_access_token` / `create_refresh_token` 으로 HS256 기반 JWT를 발급.
- `verify_token` 은 블랙리스트 여부를 Redis/인메모리로 확인한 뒤 JWT를 디코드합니다.
- **좋은 점**
  - `TokenData` Pydantic 모델을 통해 **토큰 페이로드를 타입 세이프하게 다루는 구조**입니다.
- **개선 포인트**
  - 비밀번호/토큰 관련 에러를 현재는 `JWTError` catch 후 None으로 돌려주는데,  
    `AuthenticationError`, `InvalidTokenError` 같은 커스텀 예외를 적극 활용하면 API 레이어에서 더 풍부한 오류 정보를 줄 수 있습니다.

#### 1.3.3. 권한 체크/토큰 블랙리스트 (L239–L281, L283–L297)

- Redis가 있으면 `blacklist:{jti}` 키로 TTL 기반 블랙리스트, 그렇지 않으면 인메모리 셋 사용.
- `has_permission`/`has_any_permission`/`has_all_permissions` 로 권한 검사.
- **좋은 점**
  - JWT 자체는 stateless지만, 블랙리스트를 도입해 로그아웃/토큰 폐기도 지원합니다.
- **개선 포인트**
  - `ROLE_PERMISSIONS` 와의 연결은 있지만, 어떤 엔드포인트에 어떤 Permission이 필요한지는 분산되어 있을 가능성이 큽니다.
    - FastAPI 라우트 단에서 데코레이터나 Depends 기반으로 **권한 요구 사항을 명시하는 패턴**을 도입하면 더 좋습니다.

---

## 2. MCP/Supadata 통합 (`mcp_integration.py`, `supadata_mcp.py`)

### 2.1. `MCPIntegrationService` (`src/services/mcp_integration.py`)

- **역할**
  - HttpMCP / WebSearchMCP / YouTubeMCP / SupadataMCP 를 조합해,  
    각 에이전트에서 필요한 **외부 웹·YouTube·스크래핑 데이터를 컨텍스트에 주입**하는 서비스입니다.
- **핵심 흐름**
  - `enrich_context(spec, user_context)`:
    - spec에서 웹/유튜브/Supadata 스펙을 추출 → `_fetch_web_data`/`_fetch_youtube_data`/`_fetch_supadata` 호출.
    - 외부 데이터를 `external_snippets`, `youtube_insights`, `supadata` 등 키로 묶어서 반환.
- **좋은 점**
  - MCP 기반 외부 의존성을 하나의 서비스로 캡슐화해서, 에이전트가 외부 API 세부사항을 알 필요가 없습니다.
- **개선 포인트**
  - `_fetch_youtube_data` 에서 `asyncio.to_thread` 로 동기 MCP 클라이언트를 감싸는데,  
    예외 처리/타임아웃 정책이 상대적으로 약하므로 **서킷 브레이커나 timeout wrapper** 를 함께 사용하는 것이 좋습니다.

### 2.2. `SupadataMCPClient` (`src/services/supadata_mcp.py`)

- **역할**
  - Supadata MCP에 대한 **thin wrapper**로, scrape/transcript/map/crawl 도구를 병렬 실행해 결과를 수집합니다.
- **학습 포인트**
  - `_gather_results` 에서 `asyncio.gather(..., return_exceptions=True)` 패턴을 사용해,  
    **일부 URL만 실패하더라도 전체 작업은 계속 진행**하게 설계된 점은 실무적인 패턴입니다.
- **개선 포인트**
  - MCP 클라이언트 초기화 실패 시 `available=False` 로 두지만,  
    상위 레이어에서 이 상태를 모니터링할 수 있는 헬스체크/메트릭이 추가되면 운영이 수월해집니다.

---

## 3. Celery 태스크 (`src/tasks`)

### 3.1. `analytics_tasks.py` – 감사/분석 리포트 작업

- 여러 태스크(`generate_daily_report`, `cleanup_old_audit_logs`, `generate_creator_analytics`, `export_audit_logs`)가  
  **audit_service와 긴밀히 결합된 “운영 리포팅/정리 작업”**을 담당합니다.
- 주목할 패턴:
  - 각 태스크는 **새 이벤트 루프를 만들어 비동기 서비스를 동기 Celery에서 호출**하는 패턴 사용.
  - 작업이 끝나면 audit_service.log 로 **자기 자신을 감사에 남기는 “메타 로깅”**을 합니다.
- **비판/개선**
  - Celery 태스크마다 `asyncio.new_event_loop()`/`loop.run_until_complete()`/`loop.close()` 를 반복합니다.
    - 공통 헬퍼(예: `run_async(coro)`)로 추출하거나, Celery를 아예 `asyncio` 기반 실행으로 구성할 수 있다면 더 깔끔해집니다.

### 3.2. `data_collection_tasks.py` – 외부 데이터 수집 작업

- NILE/MOHW/KICCE 등 공공 데이터 소스를 `DataCollectionAgent` 를 통해 수집하고,  
  `collect_all_external_data` 에서 각 태스크를 한 번에 트리거하면서 감사 로그를 남깁니다.
- **좋은 점**
  - 데이터 수집 로직은 에이전트에 위임하고, Celery 태스크는 **스케줄링/감사/실패 재시도 정책**에 집중합니다.
- **비판/개선**
  - 각 태스크에서 `asyncio` 루프를 직접 생성/종료하는 중복이 많습니다.

### 3.3. `index_documents_to_vector_db`

- RAGPipeline을 만든 다음 `retrieval_engine.add_documents`를 호출해 벡터 DB에 문서를 인덱싱합니다.
- **학습 포인트**
  - “코어 파이프라인(RAGPipeline)을 재사용해 오프라인 인덱싱 작업을 수행하는 패턴”을 잘 보여줍니다.
- **개선 포인트**
  - 여기서도 모델/키 등 설정은 `get_settings()` 에서 바로 가져옵니다.
    - 장기적으로는 “태스크용 pipeline config builder” 를 하나 두고 재사용하면 더 좋습니다.

---

## 4. 모니터링 (`src/monitoring`)

### 4.1. `performance_monitor.py` – PerformanceMonitor

- **역할**
  - `start_operation` / `end_operation` 으로 **任意 작업의 레이턴시/성공 여부**를 추적하고,  
    히스토리/에러율/백분위수(P95/P99)를 계산합니다.
- **좋은 점**
  - 간단한 구조지만, **“모든 작업에 공통으로 쓰이는 성능 모니터링 레이어”**로 확장할 수 있는 기반이 마련되어 있습니다.
- **개선 포인트**
  - 현재 구현은 단일 프로세스 메모리에만 저장되므로, 다중 인스턴스 환경에서는 **프로메테우스/타임시리즈 DB에 push**하는 방식으로 확장해야 합니다.

### 4.2. `metrics_collector.py` – MetricsCollector

- **역할**
  - psutil 기반 시스템 메트릭(CPU/메모리/디스크/네트워크/프로세스)과  
    LangGraph/RAG/애플리케이션 메트릭을 함께 수집/요약하는 유틸입니다.
- **학습 포인트**
  - `collect_langgraph_metrics` 에서 Deep Agents 관련 지표(`retry_count`, `no_progress_count`, `avg_critic_score`)를 누적하는 패턴은  
    “에이전트/워크플로우 특화 메트릭 설계”의 좋은 예시입니다.
- **개선 포인트**
  - 시스템 메트릭 수집에 1초 블로킹(`cpu_percent(interval=1)`)을 사용하므로, 이 메서드는 **주기적인 백그라운드 작업**에서만 호출해야 합니다.

---

## 5. 코어 인프라 (`src/core/circuit_breaker.py`, `src/core/exceptions.py`)

### 5.1. `circuit_breaker.py`

- pybreaker를 감싼 `CircuitBreakerManager` + `circuit_breaker` 데코레이터로,  
  외부 API 실패 시 서킷을 열고 폴백 함수를 호출하는 패턴을 제공합니다.
- **좋은 점**
  - sync/async 함수를 모두 지원하는 wrapper를 제공해, 다양한 호출 컨텍스트에서 재사용할 수 있습니다.
  - 사전 정의된 `CIRCUIT_BREAKER_CONFIGS` 로 기본 정책을 중앙 관리합니다.
- **개선 포인트**
  - `_stats["state_changes"]` 필드를 정의해 놓고 실제 state change 시점에 채우고 있지 않습니다.
    - listener에서 state 변화 이벤트를 `_stats` 에 push 하면, 나중에 **서킷 변동 이력**을 볼 수 있습니다.

### 5.2. `exceptions.py`

- **역할**
  - 전역에서 사용할 표준화된 예외 계층 (Validation/Auth/DB/API/Agent/Data/Config 등)을 정의합니다.
  - `handle_exception` & `create_error_response` 를 통해 로깅과 API 응답 생성을 일관되게 처리할 수 있게 합니다.
- **좋은 점**
  - 에러 분류/심각도 개념을 코드 레벨에서 강제하기 때문에, 에이전트/서비스 코드가  
    “어떤 종류의 실패인지”를 명확히 표현하는 데 도움을 줍니다.
- **개선 포인트**
  - 실제 FastAPI 라우트에서 이 예외들을 얼마나 적극적으로 사용하고 있는지 확인하고,  
    미들웨어 레벨에서 `BaseApplicationException` 을 잡아 API 에러 응답으로 변환하는 **글로벌 핸들러**를 추가하면 좋습니다.

---

## 6. 미들웨어 (`src/api/middleware`)

### 6.1. `rate_limit.py` – RateLimitMiddleware

- **역할**
  - IP 기반 토큰 버킷/고정 윈도우 조합으로 요청 수를 제한하고, Redis나 in-memory를 백엔드로 사용합니다.
- **학습 포인트**
  - `_check_rate_limit` (메모리), `_check_rate_limit_redis` (Redis) 두 경로를 분리해,  
    sync/async 제약을 코드로 명확히 표현합니다.
- **개선 포인트**
  - 현재는 IP만 기준으로 합니다:
    - API key/사용자 ID/엔드포인트 별로 세분화된 rate limit 이 필요해질 수 있습니다.
  - Redis 모드에서 예외 발생 시 메모리로 폴백하지만, 이 경우 운영자에게 알려줄 수 있는 메트릭/알람이 추가되면 좋습니다.

### 6.2. `correlation.py` – CorrelationIdMiddleware

- **역할**
  - `X-Request-ID` 헤더를 생성/전파하고, `logging_setup.bind_request` 로 구조적 로깅에 request_id 를 바인딩합니다.
- **좋은 점**
  - request 단위 트레이싱의 기본 패턴을 깔끔하게 구현했습니다.
- **개선 포인트**
  - 에러 응답이나 WebSocket 등 특수 케이스에서도 request_id가 항상 전파되는지 확인하고,  
    필요하다면 추가 미들웨어/exception handler에서 보완할 수 있습니다.

---

## 7. 테스트 코드 (`tests/*`)

### 7.1. E2E: `tests/e2e/test_creator_mission_flow.py`

- CreatorOnboardingAgent → MissionAgent 로 이어지는 **엔드 투 엔드 플로우**를 테스트합니다.
- **학습 포인트**
  - 테스트에서 실제로 `CreatorOnboardingAgent.execute()` 의 결과를 MissionAgent의 입력으로 사용하는 패턴은,  
    “에이전트 간 인터페이스가 잘 설계되어 있는지”를 검증하는 좋은 예시입니다.

### 7.2. Rate limit: `tests/integration/test_rate_limit.py`

- 작은 FastAPI 앱을 만들고 `RateLimitMiddleware` 만 붙인 뒤, `/ping` 엔드포인트에 3회 호출하여  
  2회까지 200, 3회째 429 를 기대합니다.
- **배울 점**
  - 미들웨어/크로스컷팅 Concern은 **작은 테스트 전용 앱을 만들어 통합 테스트**하는 패턴이 효과적입니다.

### 7.3. Generation fallback: `tests/unit/rag/test_generation_fallback.py`

- `GenerationEngine` 에 커스텀 `FailingModel` 인스턴스를 주입해,  
  - 첫 번째 모델은 실패, fallback 모델이 성공하는 경우,
  - retry로 결국 같은 모델이 성공하는 경우를 단위 테스트합니다.
- **학습 포인트**
  - 외부 LLM 호출 없이도 “재시도/폴백 정책”을 테스트할 수 있도록 설계된 구조는,  
    에이전트/플릿 로직을 구현할 때 참고할 만한 좋은 예입니다.

---

## 8. 에이전트 개발자를 위한 3차 학습 요약

- **1) 운영 관점의 서비스 레이어를 이해하라**
  - ABTesting/Audit/Auth/MCP/Supadata 서비스들은 전부 **에이전트의 품질과 운영 안정성**을 지탱하는 인프라입니다.
  - 에이전트를 설계할 때, “이 에이전트의 결과/오류/프롬프트 변화가 어떻게 감사/모니터링/AB테스트에 반영되는가?”를 항상 의식하는 연습이 필요합니다.

- **2) 비동기 + Celery + DB/외부 API의 경계면을 신중하게 다뤄라**
  - 현재 코드는 `asyncio + 동기 SQLAlchemy + Celery` 가 섞여 있어, 구조는 유연하지만 복잡합니다.
  - 이 경계에서 **블로킹/리소스 누수/이중 루프 생성** 같은 문제가 생기지 않도록, 공통 헬퍼/추상화를 점진적으로 도입하는 것이 좋습니다.

- **3) 테스트는 “행복 경로”만이 아니라 “플릿/폴백/제한/에러”를 검증해야 한다**
  - Generation fallback, rate limit, creator→mission flow 테스트는 모두 “문제가 생겼을 때 시스템이 어떻게 반응하는지”를 검증합니다.
  - 에이전트 개발자는 새 기능을 만들 때, **이 세 가지 축(성공 플로우/한계 조건/에러·폴백)**에 대해 항상 테스트를 고민해야 합니다.

이 3차 문서는 앞서 만든
- `docs/gpt5_migration_code_review.md`
- `docs/agents_api_rag_code_review.md`

와 함께 보면, **모델/플릿 → 오케스트레이션/RAG → 서비스/운영/테스트** 까지 전체 스택을 종합적으로 이해하는 데 도움이 됩니다.


