---
description: Langfuse → Grafana 모니터링 대시보드
argument-hint: "[action] [target]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Monitor Agent

Langfuse 트레이싱과 Grafana 대시보드를 설정합니다.

## Instructions

1. Langfuse 트레이싱 설정:
   - RAG 파이프라인 트레이스
   - LLM 토큰 사용량 추적
   - 비용 모니터링

2. Grafana 대시보드:
   - Request rate by model
   - Token usage over time
   - Latency P50/P95/P99

3. 알림 채널 설정:
   - Slack webhook
   - Email notification

## Arguments
- `$ARGUMENTS` - 설정 대상 및 액션

## Langfuse Metrics
- Trace duration
- Token usage (input/output)
- Cost per request
- Success/failure rates

## Key Files
- `src/monitoring/langfuse.py`
- `src/monitoring/tracing.py`
- `src/monitoring/metrics_collector.py`
