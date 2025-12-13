"""
Celery 애플리케이션 설정
"""

import os
from celery import Celery

from config.settings import get_settings

settings = get_settings()

# Celery 애플리케이션 생성
celery_app = Celery(
    "creator_onboarding",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "src.tasks.data_collection_tasks",
        "src.tasks.analytics_tasks",
        "src.tasks.notification_tasks",
    ],
)

# Celery 설정
celery_app.conf.update(
    # Task 설정
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
    # 작업 결과 만료 시간 (24시간)
    result_expires=86400,
    # 워커 설정
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    # 재시도 설정
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Beat 스케줄러 (주기적 작업)
    beat_schedule={
        "collect-external-data-hourly": {
            "task": "src.tasks.data_collection_tasks.collect_all_external_data",
            "schedule": 3600.0,  # 1시간마다
        },
        "cleanup-old-audit-logs-daily": {
            "task": "src.tasks.analytics_tasks.cleanup_old_audit_logs",
            "schedule": 86400.0,  # 24시간마다
        },
        "generate-daily-analytics-report": {
            "task": "src.tasks.analytics_tasks.generate_daily_report",
            "schedule": 86400.0,  # 24시간마다
        },
    },
    # 작업 라우팅
    task_routes={
        "src.tasks.data_collection_tasks.*": {"queue": "data_collection"},
        "src.tasks.analytics_tasks.*": {"queue": "analytics"},
        "src.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    # 동시성 제한
    task_default_rate_limit="100/m",
)


# Celery 워커 실행 시: celery -A src.tasks.celery_app worker -l info
# Celery Beat 실행 시: celery -A src.tasks.celery_app beat -l info
# Flower 모니터링: celery -A src.tasks.celery_app flower
