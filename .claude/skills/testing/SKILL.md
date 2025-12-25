---
name: testing
description: 테스트 작성 및 커버리지 관리 스킬. 단위 테스트, 통합 테스트, E2E 테스트 작업 시 자동으로 활성화됩니다. pytest, test, coverage, mock, fixture 키워드에 반응합니다.
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Testing Skill

Python pytest 및 Cypress E2E 테스트 전문 스킬입니다.

## 핵심 역량

### 1. 단위 테스트 (Unit Tests)
- pytest 기반 테스트 작성
- Mock/Patch 활용
- Fixture 관리

### 2. 통합 테스트 (Integration Tests)
- API 엔드포인트 테스트
- 데이터베이스 연동 테스트
- 외부 서비스 테스트

### 3. E2E 테스트
- Cypress 테스트 작성
- 사용자 플로우 테스트

### 4. 커버리지 관리
- 목표: 95% 커버리지
- 누락 라인 식별
- 커버리지 리포트 분석

## 프로젝트 구조

```
tests/
├── conftest.py          # 공통 fixtures
├── unit/
│   ├── agents/
│   ├── rag/
│   └── services/
├── integration/
│   ├── test_mission_api.py
│   └── test_rate_limit.py
└── e2e/
    └── test_creator_mission_flow.py
```

## 테스트 패턴

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_llm_client():
    client = AsyncMock()
    client.generate.return_value = "mocked response"
    return client

@pytest.mark.asyncio
async def test_rag_pipeline_success(mock_llm_client):
    """RAG 파이프라인 정상 동작 테스트"""
    with patch("src.rag.generation_engine.get_client", return_value=mock_llm_client):
        pipeline = RAGPipeline()
        result = await pipeline.process_query("test query")

        assert result["success"] is True
        assert "response" in result

def test_creator_schema_validation():
    """크리에이터 스키마 유효성 테스트"""
    with pytest.raises(ValidationError):
        CreatorRequest(name="", category="tech")
```

## 커맨드

```bash
# 전체 테스트 실행
pytest tests/ -v

# 커버리지 리포트
pytest --cov=src --cov-report=html tests/

# 특정 모듈 테스트
pytest tests/unit/rag/ -v

# 병렬 실행
pytest -n auto tests/
```

## 커버리지 목표

| 모듈 | 현재 | 목표 |
|------|------|------|
| src/rag/ | 85% | 95% |
| src/agents/ | 80% | 95% |
| src/api/ | 90% | 95% |
