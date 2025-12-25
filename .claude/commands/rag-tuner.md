---
description: RAG 파이프라인 최적화 및 프롬프트 A/B 테스트
argument-hint: "[action] [params]"
allowed-tools: Read, Edit, Grep, Glob, Bash
---

# RAG Tuner

RAG 파이프라인을 분석하고 최적화합니다.

## Instructions

1. 먼저 현재 RAG 설정을 확인합니다:
   - `config/settings.py` - RERANKER_THRESHOLD, QUERY_EXPANSION_ENABLED
   - `src/rag/retrieval_engine.py` - similarity_threshold, rerank_top_k
   - `src/rag/query_expander.py` - n_variations

2. 사용자 요청에 따라 파라미터를 조정합니다:
   - rerank threshold 조정 (0.0 ~ 1.0)
   - multi-query expansion count 조정
   - hybrid search 가중치 조정

3. 변경 후 영향도를 분석합니다.

## Arguments
- `$ARGUMENTS` - 최적화 지시사항 (예: "rerank 0.85, multi-query 5")

## Key Files
- `src/rag/rag_pipeline.py`
- `src/rag/retrieval_engine.py`
- `src/rag/query_expander.py`
- `config/settings.py`
