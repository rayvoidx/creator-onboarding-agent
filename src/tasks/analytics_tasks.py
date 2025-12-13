"""
분석 및 리포팅 관련 Celery 작업
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from celery import shared_task

from src.services.audit.service import get_audit_service
from src.data.models.audit_models import AuditAction, AuditSeverity, AuditLogQuery

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_daily_report(self) -> Dict[str, Any]:
    """
    일일 분석 리포트 생성
    """
    logger.info(f"Starting daily report generation. Task ID: {self.request.id}")

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 감사 로그 통계 수집
            audit_service = get_audit_service()

            # 지난 24시간 데이터
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=1)

            stats = loop.run_until_complete(
                audit_service.get_stats(start_date, end_date)
            )

            report = {
                "report_type": "daily",
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                },
                "metrics": {
                    "total_requests": stats.get("total_logs", 0),
                    "success_rate": stats.get("success_rate", 0),
                    "action_breakdown": stats.get("action_counts", {}),
                    "severity_breakdown": stats.get("severity_counts", {}),
                    "top_users": dict(
                        sorted(
                            stats.get("user_counts", {}).items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )[:10]
                    ),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

            # 리포트 생성 감사 로그
            loop.run_until_complete(
                audit_service.log(
                    action=AuditAction.ANALYTICS_REPORT,
                    details={
                        "report_type": "daily",
                        "metrics_summary": {
                            "total_requests": report["metrics"]["total_requests"],
                            "success_rate": report["metrics"]["success_rate"],
                        },
                    },
                    severity=AuditSeverity.INFO,
                )
            )

        finally:
            loop.close()

        logger.info(
            f"Daily report generated: {report['metrics']['total_requests']} requests"
        )

        return {
            "success": True,
            "report": report,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(f"Daily report generation failed: {e}")
        raise


@shared_task(bind=True)
def cleanup_old_audit_logs(self, days_to_keep: int = 90) -> Dict[str, Any]:
    """
    오래된 감사 로그 정리

    Args:
        days_to_keep: 보관할 일수 (기본 90일)
    """
    logger.info(
        f"Starting audit log cleanup. Task ID: {self.request.id}, Days to keep: {days_to_keep}"
    )

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            audit_service = get_audit_service()

            # 메모리 기반인 경우 간단히 필터링
            if audit_service._use_memory:
                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
                original_count = len(audit_service._logs)
                audit_service._logs = [
                    log for log in audit_service._logs if log.timestamp >= cutoff_date
                ]
                deleted_count = original_count - len(audit_service._logs)
            else:
                # PostgreSQL에서는 DELETE 쿼리 실행
                from sqlalchemy import create_engine, delete
                from sqlalchemy.orm import sessionmaker
                from src.services.audit.service import AuditLogTable

                cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

                sync_url = audit_service.database_url.replace("+asyncpg", "")
                engine = create_engine(sync_url)
                Session = sessionmaker(bind=engine)
                session = Session()

                try:
                    result = session.execute(
                        delete(AuditLogTable).where(
                            AuditLogTable.timestamp < cutoff_date
                        )
                    )
                    deleted_count = result.rowcount
                    session.commit()
                finally:
                    session.close()
                    engine.dispose()

            # 정리 작업 감사 로그
            loop.run_until_complete(
                audit_service.log(
                    action=AuditAction.SYSTEM_CONFIG_CHANGE,
                    details={
                        "operation": "audit_log_cleanup",
                        "days_kept": days_to_keep,
                        "deleted_count": deleted_count,
                    },
                    severity=AuditSeverity.INFO,
                )
            )

        finally:
            loop.close()

        logger.info(f"Audit log cleanup completed: {deleted_count} logs deleted")

        return {
            "success": True,
            "deleted_count": deleted_count,
            "days_kept": days_to_keep,
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Audit log cleanup failed: {e}")
        raise


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def generate_creator_analytics(
    self, creator_id: str, period_days: int = 30
) -> Dict[str, Any]:
    """
    특정 크리에이터에 대한 분석 리포트 생성

    Args:
        creator_id: 크리에이터 ID
        period_days: 분석 기간 (일)
    """
    logger.info(
        f"Starting creator analytics. Task ID: {self.request.id}, "
        f"Creator: {creator_id}, Period: {period_days} days"
    )

    try:
        import asyncio

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            audit_service = get_audit_service()

            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=period_days)

            # 해당 크리에이터 관련 로그 조회
            query = AuditLogQuery(
                resource_type="creator",
                resource_id=creator_id,
                start_date=start_date,
                end_date=end_date,
                limit=10000,
            )

            result = loop.run_until_complete(audit_service.query(query))

            # 분석 집계
            action_counts: Dict[str, int] = {}
            for log in result.logs:
                action_counts[log.action.value] = (
                    action_counts.get(log.action.value, 0) + 1
                )

            analytics = {
                "creator_id": creator_id,
                "period": {
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "days": period_days,
                },
                "metrics": {
                    "total_activities": result.total,
                    "action_breakdown": action_counts,
                    "evaluations": action_counts.get("creator_evaluate", 0),
                    "mission_recommendations": action_counts.get(
                        "mission_recommend", 0
                    ),
                },
                "generated_at": datetime.utcnow().isoformat(),
            }

        finally:
            loop.close()

        logger.info(
            f"Creator analytics generated: {analytics['metrics']['total_activities']} activities"
        )

        return {
            "success": True,
            "analytics": analytics,
            "task_id": self.request.id,
        }

    except Exception as e:
        logger.error(f"Creator analytics generation failed: {e}")
        raise


@shared_task(bind=True)
def export_audit_logs(
    self, format: str = "json", start_date: str = None, end_date: str = None
) -> Dict[str, Any]:
    """
    감사 로그 내보내기

    Args:
        format: 출력 형식 (json, csv)
        start_date: 시작 날짜 (ISO 형식)
        end_date: 종료 날짜 (ISO 형식)
    """
    logger.info(
        f"Starting audit log export. Task ID: {self.request.id}, Format: {format}"
    )

    try:
        import asyncio
        import json

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            audit_service = get_audit_service()

            query = AuditLogQuery(
                start_date=datetime.fromisoformat(start_date) if start_date else None,
                end_date=datetime.fromisoformat(end_date) if end_date else None,
                limit=100000,  # 대량 내보내기
            )

            result = loop.run_until_complete(audit_service.query(query))

            # 파일 저장
            import os

            export_dir = "./exports"
            os.makedirs(export_dir, exist_ok=True)

            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{export_dir}/audit_logs_{timestamp}.{format}"

            if format == "json":
                with open(filename, "w") as f:
                    logs_data = [log.model_dump() for log in result.logs]
                    # datetime 직렬화 처리
                    for log in logs_data:
                        for key, value in log.items():
                            if isinstance(value, datetime):
                                log[key] = value.isoformat()
                    json.dump(logs_data, f, indent=2, ensure_ascii=False, default=str)
            elif format == "csv":
                import csv

                with open(filename, "w", newline="") as f:
                    if result.logs:
                        fieldnames = list(result.logs[0].model_dump().keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        writer.writeheader()
                        for log in result.logs:
                            row = log.model_dump()
                            for key, value in row.items():
                                if isinstance(value, (dict, list)):
                                    row[key] = json.dumps(value, ensure_ascii=False)
                                elif isinstance(value, datetime):
                                    row[key] = value.isoformat()
                            writer.writerow(row)

            # 내보내기 감사 로그
            loop.run_until_complete(
                audit_service.log(
                    action=AuditAction.DATA_EXPORT,
                    details={
                        "format": format,
                        "filename": filename,
                        "record_count": len(result.logs),
                    },
                    severity=AuditSeverity.INFO,
                )
            )

        finally:
            loop.close()

        logger.info(f"Audit log export completed: {filename}")

        return {
            "success": True,
            "filename": filename,
            "record_count": len(result.logs),
            "format": format,
            "task_id": self.request.id,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Audit log export failed: {e}")
        raise
