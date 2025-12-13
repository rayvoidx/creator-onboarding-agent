"""Monitoring endpoints."""

import logging
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.app.dependencies import MONITORING_AVAILABLE, get_dependencies

# Optional Prometheus imports
try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    from src.monitoring.prometheus_exporter import build_registry

    PROM_AVAILABLE = True
except Exception:
    PROM_AVAILABLE = False

router = APIRouter(tags=["Monitoring"])
logger = logging.getLogger(__name__)


@router.get("/api/v1/monitoring/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance metrics."""
    try:
        deps = get_dependencies()

        if not MONITORING_AVAILABLE or not deps.performance_monitor:
            return {
                "success": False,
                "message": "Monitoring system not available. Install langfuse and psutil for full monitoring.",
                "timestamp": datetime.now().isoformat(),
            }

        performance_summary = deps.performance_monitor.get_performance_summary()

        return {
            "success": True,
            "performance_metrics": performance_summary,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"Performance metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail="성능 메트릭 조회 중 오류가 발생했습니다."
        )


@router.get("/api/v1/monitoring/system")
async def get_system_metrics() -> Dict[str, Any]:
    """Get system metrics."""
    try:
        deps = get_dependencies()

        if not deps.metrics_collector:
            raise HTTPException(
                status_code=500, detail="메트릭 수집기가 초기화되지 않았습니다."
            )

        system_metrics = await deps.metrics_collector.collect_system_metrics()
        metrics_summary = deps.metrics_collector.get_metrics_summary(hours=1)

        return {
            "success": True,
            "system_metrics": system_metrics,
            "metrics_summary": metrics_summary,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"System metrics retrieval failed: {e}")
        raise HTTPException(
            status_code=500, detail="시스템 메트릭 조회 중 오류가 발생했습니다."
        )


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus metrics exposition (on-demand snapshot)."""
    if not PROM_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prometheus exporter not available")

    try:
        deps = get_dependencies()

        if deps.metrics_collector:
            try:
                await deps.metrics_collector.collect_system_metrics()
            except Exception:
                pass

        registry = build_registry(deps.performance_monitor, deps.metrics_collector)
        data = generate_latest(registry)
        return StreamingResponse(iter([data]), media_type=CONTENT_TYPE_LATEST)

    except Exception as e:
        logger.error(f"Prometheus metrics generation failed: {e}")
        raise HTTPException(status_code=500, detail="메트릭 노출 중 오류")
