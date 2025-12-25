---
description: MCP 서버 및 벡터 인덱스 최적화
argument-hint: "[target] [config]"
allowed-tools: Read, Edit, Grep, Glob, Bash
---

# MCP Optimizer

MCP 서버 설정과 벡터 인덱스를 최적화합니다.

## Instructions

1. MCP 서버 설정을 분석합니다:
   - Circuit Breaker 설정 (fail_max, reset_timeout)
   - Retry/Backoff 정책
   - Timeout 설정

2. Pinecone 인덱스 최적화:
   - Namespace 전략 검토
   - Metadata 필터링 최적화

3. 임베딩 성능 비교 (Voyage-3 vs OpenAI)

## Arguments
- `$ARGUMENTS` - 최적화 대상 및 설정

## Key Files
- `src/mcp/servers/vector_search_server.py`
- `src/mcp/servers/http_fetch_server.py`
- `src/services/mcp_integration.py`
- `config/settings.py` (MCP_* 설정)
