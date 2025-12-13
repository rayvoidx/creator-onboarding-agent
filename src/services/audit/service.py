"""
감사 추적 서비스 - 모든 중요 작업을 기록
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import (
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import sessionmaker as async_sessionmaker

from config.settings import get_settings
from src.data.models.audit_models import (
    AuditAction,
    AuditLog,
    AuditLogCreate,
    AuditLogQuery,
    AuditLogResponse,
    AuditSeverity,
)

logger = logging.getLogger(__name__)
settings = get_settings()

Base = declarative_base()


class AuditLogTable(Base):
    """감사 로그 SQLAlchemy 모델"""

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # 사용자 정보
    user_id = Column(String(36), index=True, nullable=True)
    username = Column(String(100), nullable=True)
    role = Column(String(50), nullable=True)

    # 이벤트 정보
    action = Column(String(50), index=True, nullable=False)
    severity = Column(String(20), default="info")
    resource_type = Column(String(50), index=True, nullable=True)
    resource_id = Column(String(100), index=True, nullable=True)

    # 요청 정보
    request_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)  # IPv6 지원
    user_agent = Column(String(500), nullable=True)
    endpoint = Column(String(500), nullable=True)
    method = Column(String(10), nullable=True)

    # 상세 정보
    details = Column(JSON, default=dict)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)

    # 결과
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)


class AuditService:
    """감사 추적 서비스"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL

        # SQLite를 사용하는 경우 파일 기반으로 폴백
        if "sqlite" in self.database_url:
            self._use_memory = True
            self._logs: List[AuditLog] = []
        else:
            self._use_memory = False
            self._engine = None
            self._session_factory = None

        self._initialized = False

    async def initialize(self) -> None:
        """데이터베이스 초기화"""
        if self._initialized:
            return

        if not self._use_memory:
            try:
                # 동기 엔진으로 테이블 생성
                sync_url = self.database_url.replace("+asyncpg", "").replace(
                    "postgresql://", "postgresql://"
                )
                engine = create_engine(sync_url)
                Base.metadata.create_all(engine)
                engine.dispose()

                logger.info("Audit tables created successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to create audit tables, falling back to memory: {e}"
                )
                self._use_memory = True
                self._logs = []

        self._initialized = True

    async def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        username: Optional[str] = None,
        role: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        request_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        endpoint: Optional[str] = None,
        method: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        old_value: Optional[Dict[str, Any]] = None,
        new_value: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        severity: AuditSeverity = AuditSeverity.INFO,
    ) -> AuditLog:
        """감사 로그 기록"""
        await self.initialize()

        audit_log = AuditLog(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            username=username,
            role=role,
            action=action,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            ip_address=ip_address,
            user_agent=user_agent,
            endpoint=endpoint,
            method=method,
            details=details or {},
            old_value=old_value,
            new_value=new_value,
            success=success,
            error_message=error_message,
        )

        if self._use_memory:
            self._logs.append(audit_log)
            # 메모리 제한 (최대 10000개)
            if len(self._logs) > 10000:
                self._logs = self._logs[-10000:]
        else:
            await self._persist_log(audit_log)

        # 중요 이벤트는 추가 로깅
        if severity in [AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            logger.warning(
                f"Audit [{severity.value}]: {action.value} by {username or 'system'} - "
                f"{error_message or 'success'}"
            )
        else:
            logger.debug(f"Audit: {action.value} by {username or 'system'}")

        return audit_log

    async def _persist_log(self, audit_log: AuditLog) -> None:
        """PostgreSQL에 로그 저장"""
        try:
            sync_url = self.database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                db_log = AuditLogTable(
                    id=audit_log.id,
                    timestamp=audit_log.timestamp,
                    user_id=audit_log.user_id,
                    username=audit_log.username,
                    role=audit_log.role,
                    action=audit_log.action.value,
                    severity=audit_log.severity.value,
                    resource_type=audit_log.resource_type,
                    resource_id=audit_log.resource_id,
                    request_id=audit_log.request_id,
                    ip_address=audit_log.ip_address,
                    user_agent=audit_log.user_agent,
                    endpoint=audit_log.endpoint,
                    method=audit_log.method,
                    details=audit_log.details,
                    old_value=audit_log.old_value,
                    new_value=audit_log.new_value,
                    success=audit_log.success,
                    error_message=audit_log.error_message,
                )
                session.add(db_log)
                session.commit()
            finally:
                session.close()
                engine.dispose()

        except Exception as e:
            logger.error(f"Failed to persist audit log: {e}")
            # 폴백으로 메모리에 저장
            if not hasattr(self, "_logs"):
                self._logs = []
            self._logs.append(audit_log)

    async def query(self, query: AuditLogQuery) -> AuditLogResponse:
        """감사 로그 조회"""
        await self.initialize()

        if self._use_memory:
            return await self._query_memory(query)
        else:
            return await self._query_database(query)

    async def _query_memory(self, query: AuditLogQuery) -> AuditLogResponse:
        """메모리에서 로그 조회"""
        filtered = self._logs.copy()

        # 필터링
        if query.user_id:
            filtered = [l for l in filtered if l.user_id == query.user_id]
        if query.action:
            filtered = [l for l in filtered if l.action == query.action]
        if query.severity:
            filtered = [l for l in filtered if l.severity == query.severity]
        if query.resource_type:
            filtered = [l for l in filtered if l.resource_type == query.resource_type]
        if query.resource_id:
            filtered = [l for l in filtered if l.resource_id == query.resource_id]
        if query.start_date:
            filtered = [l for l in filtered if l.timestamp >= query.start_date]
        if query.end_date:
            filtered = [l for l in filtered if l.timestamp <= query.end_date]
        if query.success is not None:
            filtered = [l for l in filtered if l.success == query.success]

        # 시간순 정렬 (최신순)
        filtered.sort(key=lambda x: x.timestamp, reverse=True)

        total = len(filtered)
        paginated = filtered[query.offset : query.offset + query.limit]

        return AuditLogResponse(
            logs=paginated,
            total=total,
            limit=query.limit,
            offset=query.offset,
        )

    async def _query_database(self, query: AuditLogQuery) -> AuditLogResponse:
        """PostgreSQL에서 로그 조회"""
        try:
            sync_url = self.database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                from sqlalchemy import and_, desc

                conditions = []
                if query.user_id:
                    conditions.append(AuditLogTable.user_id == query.user_id)
                if query.action:
                    conditions.append(AuditLogTable.action == query.action.value)
                if query.severity:
                    conditions.append(AuditLogTable.severity == query.severity.value)
                if query.resource_type:
                    conditions.append(
                        AuditLogTable.resource_type == query.resource_type
                    )
                if query.resource_id:
                    conditions.append(AuditLogTable.resource_id == query.resource_id)
                if query.start_date:
                    conditions.append(AuditLogTable.timestamp >= query.start_date)
                if query.end_date:
                    conditions.append(AuditLogTable.timestamp <= query.end_date)
                if query.success is not None:
                    conditions.append(AuditLogTable.success == query.success)

                # 총 개수
                total_query = session.query(AuditLogTable)
                if conditions:
                    total_query = total_query.filter(and_(*conditions))
                total = total_query.count()

                # 페이지네이션
                results = (
                    session.query(AuditLogTable).filter(and_(*conditions))
                    if conditions
                    else session.query(AuditLogTable)
                )
                results = (
                    results.order_by(desc(AuditLogTable.timestamp))
                    .offset(query.offset)
                    .limit(query.limit)
                    .all()
                )

                logs = [
                    AuditLog(
                        id=r.id,
                        timestamp=r.timestamp,
                        user_id=r.user_id,
                        username=r.username,
                        role=r.role,
                        action=AuditAction(r.action),
                        severity=AuditSeverity(r.severity),
                        resource_type=r.resource_type,
                        resource_id=r.resource_id,
                        request_id=r.request_id,
                        ip_address=r.ip_address,
                        user_agent=r.user_agent,
                        endpoint=r.endpoint,
                        method=r.method,
                        details=r.details or {},
                        old_value=r.old_value,
                        new_value=r.new_value,
                        success=r.success,
                        error_message=r.error_message,
                    )
                    for r in results
                ]

                return AuditLogResponse(
                    logs=logs,
                    total=total,
                    limit=query.limit,
                    offset=query.offset,
                )

            finally:
                session.close()
                engine.dispose()

        except Exception as e:
            logger.error(f"Failed to query audit logs from database: {e}")
            return await self._query_memory(query)

    async def get_stats(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """감사 로그 통계"""
        query = AuditLogQuery(
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # 통계용 대량 조회
        )
        result = await self.query(query)

        # 액션별 통계
        action_counts: Dict[str, int] = {}
        severity_counts: Dict[str, int] = {}
        user_counts: Dict[str, int] = {}
        success_count = 0
        failure_count = 0

        for log in result.logs:
            # 액션별
            action_counts[log.action.value] = action_counts.get(log.action.value, 0) + 1
            # 심각도별
            severity_counts[log.severity.value] = (
                severity_counts.get(log.severity.value, 0) + 1
            )
            # 사용자별
            if log.username:
                user_counts[log.username] = user_counts.get(log.username, 0) + 1
            # 성공/실패
            if log.success:
                success_count += 1
            else:
                failure_count += 1

        return {
            "total_logs": result.total,
            "action_counts": action_counts,
            "severity_counts": severity_counts,
            "user_counts": user_counts,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_count / max(result.total, 1),
        }


# 싱글톤 인스턴스
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """감사 서비스 인스턴스 반환"""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
