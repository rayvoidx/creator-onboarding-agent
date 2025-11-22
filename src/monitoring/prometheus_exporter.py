from __future__ import annotations

"""Prometheus exporter helpers.

Build a one-shot registry from current PerformanceMonitor and MetricsCollector snapshots.
"""

from typing import Any, Optional
from prometheus_client import CollectorRegistry, Gauge


def build_registry(perf: Optional[Any], sysm: Optional[Any]) -> CollectorRegistry:
    registry = CollectorRegistry()

    # PerformanceMonitor gauges
    g_current = Gauge('app_current_operations', 'Number of in-flight operations', registry=registry)
    g_total_ops = Gauge('app_total_operations', 'Total operations observed', registry=registry)
    g_total_errors = Gauge('app_total_errors', 'Total errors observed', registry=registry)
    g_overall_error_rate = Gauge('app_overall_error_rate', 'Overall error rate', registry=registry)
    g_p95 = Gauge('app_p95_duration_seconds', 'Overall P95 latency (seconds)', registry=registry)

    if perf is not None:
        try:
            summary = perf.get_performance_summary()
            overall = summary.get('overall_stats', {}) if isinstance(summary, dict) else {}
            g_current.set(float(summary.get('current_operations', 0)))
            g_total_ops.set(float(overall.get('total_operations', 0)))
            g_total_errors.set(float(overall.get('total_errors', 0)))
            g_overall_error_rate.set(float(overall.get('overall_error_rate', 0.0)))
            g_p95.set(float(overall.get('p95_duration', 0.0)))

            # Domain-specific metrics (creator onboarding / mission recommendation)
            domain = getattr(perf, 'get_domain_metrics', None)
            if callable(domain):
                dm = domain() or {}
                g_creator_avg_score = Gauge(
                    'creator_onboarding_avg_score',
                    'Average creator onboarding score (0-100)',
                    registry=registry,
                )
                g_creator_accept_rate = Gauge(
                    'creator_onboarding_accept_rate',
                    'Creator onboarding accept decision rate (0-1)',
                    registry=registry,
                )
                g_mission_avg_per_request = Gauge(
                    'mission_recommendations_avg_per_request',
                    'Average number of missions recommended per request',
                    registry=registry,
                )
                g_creator_avg_score.set(float(dm.get('creator_avg_score', 0.0)))
                g_creator_accept_rate.set(float(dm.get('creator_accept_rate', 0.0)))
                g_mission_avg_per_request.set(float(dm.get('mission_avg_recommendations_per_request', 0.0)))
        except Exception:
            pass

    # System metrics gauges
    g_cpu = Gauge('system_cpu_percent', 'System CPU percent', registry=registry)
    g_mem = Gauge('system_memory_percent', 'System memory percent', registry=registry)
    g_disk = Gauge('system_disk_percent', 'System disk percent', registry=registry)
    g_proc_cpu = Gauge('process_cpu_percent', 'Process CPU percent', registry=registry)
    g_proc_mem = Gauge('process_memory_mb', 'Process memory MB', registry=registry)

    if sysm is not None:
        try:
            snap = sysm.metrics_history[-1] if sysm.metrics_history else {}
            cpu = (snap.get('cpu') or {}).get('percent', 0)
            mem = (snap.get('memory') or {}).get('percent', 0)
            disk = (snap.get('disk') or {}).get('percent', 0)
            p = snap.get('process') or {}
            g_cpu.set(float(cpu))
            g_mem.set(float(mem))
            g_disk.set(float(disk))
            g_proc_cpu.set(float(p.get('cpu_percent', 0)))
            g_proc_mem.set(float(p.get('memory_mb', 0)))
        except Exception:
            pass

    return registry


