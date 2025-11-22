## Phase 0 – 테스트 / 타입 / 모니터링 정리 (개발 메모)

이 문서는 `creator-onboarding-agent`의 공통 인프라/실험 환경 정리(Phase 0)에서
테스트/타입/모니터링 상태를 기록하기 위한 개발용 메모입니다.

로컬 환경에서 실제로 `pytest`, `mypy`, 서버 실행 및 엔드포인트 호출을 수행한 뒤
아래 항목을 채워 주세요.

---

### 1. pytest 실행 결과

- 실행 커맨드:
  - `pytest tests/`

- 현재 상태 요약:
  - [ ] 모든 테스트 통과
  - [ ] 일부 테스트 실패 (아래에 정리)

- 실패 테스트 목록 (예: 모듈/테스트명, 에러 요약):
  - 예시) `tests/test_creator_agent.py::test_creator_scoring_basic` – AssertionError (예상 점수 범위 밖)
  - 예시) `tests/test_rag_eval.py::...` – 외부 리소스/환경 변수 미설정 등

- 즉시 수정한 내용 (있다면 간단 요약):
  - 예시) 스코어링 로직 경계값 수정, 테스트 기대값 조정 등

- 남겨둔 이슈 / 후속 작업 메모:
  - 예시) 특정 테스트는 외부 서비스/키 필요 → 별도 integration 테스트로 분리 필요

---

### 2. mypy 실행 결과

- 실행 커맨드:
  - `mypy src/ main.py`

- 전체 요약:
  - [ ] 치명적인 타입 에러 없음
  - [ ] 경미한 타입 경고 다수 (설계 상 허용)
  - [ ] 수정이 필요한 타입 에러 존재

- 주요 타입 에러/경고 (파일/라인/요약):
  - 예시) `src/graphs/main_orchestrator.py` – `PerformanceMonitor` 가 Optional 인데 None 체크 없이 사용
  - 예시) `src/agents/...` – 반환 타입 Annotation 누락 등

- 즉시 수정한 내용 (있다면 간단 요약):
  - 예시) Optional 체크 추가, 반환 타입 Annotation 보강 등

- 추후 단계에서 처리할 타입 관련 TODO:
  - 예시) 에이전트 상태 클래스들에 대해 더 엄격한 타입 정의 도입
  - 예시) `ignore_errors=True` 섹션 축소 및 점진적 타입 안정화

---

### 3. 모니터링 엔드포인트 확인

로컬에서 서버 실행 후, 아래 엔드포인트를 호출해 상태를 기록합니다.

- 서버 실행:
  - `python main.py`

- 헬스/모니터링 엔드포인트:
  - `GET /api/v1/monitoring/performance`
  - `GET /api/v1/monitoring/system`
  - `GET /metrics`

- 실제 호출 커맨드 예시:
  - `curl http://localhost:8000/api/v1/monitoring/performance`
  - `curl http://localhost:8000/api/v1/monitoring/system`
  - `curl http://localhost:8000/metrics`

- 결과 요약:
  - `/api/v1/monitoring/performance`:
    - [ ] 200 OK
    - [ ] 200 이지만 모니터링 비활성 메시지 (예: psutil/langfuse 미설치)
    - [ ] 4xx/5xx (아래에 에러 내용 기록)
  - `/api/v1/monitoring/system`:
    - [ ] 200 OK
    - [ ] 4xx/5xx (아래에 에러 내용 기록)
  - `/metrics`:
    - [ ] 200 OK (Prometheus 메트릭 노출)
    - [ ] 503 (prometheus-client 미설치 등, 메시지 확인)

- 발견된 문제와 원인 (예시):
  - 예시) `Monitoring system not available` – `psutil` / `langfuse` 미설치 또는 환경 변수 미설정
  - 예시) `/metrics` 503 – `prometheus-client` 미설치

- 적용/계획 중인 최소 수정:
  - 예시) requirements.txt 에 필요한 패키지 추가/확인
  - 예시) 모니터링 비활성 시에도 200 + 설명 메시지로 응답하도록 핸들링 개선 검토

---

### 4. 메모

- 이 문서는 Phase 0 진행 중 수시로 갱신 가능한 워킹 문서입니다.
- 추후 Phase 1+에서 인프라/테스트 안정화가 진행되면, 이 내용을 기반으로
  보다 공식적인 개발 문서나 이슈 트래커 항목으로 승격할 수 있습니다.


