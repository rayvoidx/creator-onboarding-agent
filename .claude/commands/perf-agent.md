---
description: Prometheus alerting 및 auto-scaling 설정
argument-hint: "[metric] [threshold]"
allowed-tools: Read, Edit, Write, Grep, Glob, Bash
---

# Performance Agent

성능 모니터링 및 알림 규칙을 설정합니다.

## Instructions

1. 현재 메트릭 익스포터 확인:
   - `src/monitoring/prometheus_exporter.py`
   - `src/monitoring/metrics_collector.py`

2. 알림 규칙 설정:
   - Latency P99 > threshold
   - Error rate > threshold
   - CPU/Memory saturation

3. Auto-scaling 임계값 조정

## Arguments
- `$ARGUMENTS` - 메트릭 및 임계값 설정

## Alert Example
```yaml
- alert: HighLatency
  expr: http_request_duration_seconds{quantile="0.99"} > 0.5
  for: 5m
```

## Key Files
- `src/monitoring/prometheus_exporter.py`
- `src/monitoring/performance_monitor.py`
- `docker-compose.yml`
