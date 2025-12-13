"""
크리에이터 프로필 이력 추적 서비스 (canonical).

정식 import 경로:
- `from src.services.creator_history.service import get_creator_history_service`
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from config.settings import get_settings
from src.data.models.creator_history_models import (
    CreatorHistoryEntry,
    CreatorHistoryQuery,
    CreatorHistoryResponse,
    CreatorSnapshot,
    CreatorTrend,
)

logger = logging.getLogger(__name__)
settings = get_settings()

Base: Any = declarative_base()


class CreatorSnapshotTable(Base):
    """크리에이터 스냅샷 SQLAlchemy 모델"""

    __tablename__ = "creator_snapshots"

    id = Column(String(36), primary_key=True)
    creator_id = Column(String(100), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    platform = Column(String(50), nullable=False)
    handle = Column(String(100), nullable=False)

    followers = Column(Integer, default=0)
    avg_likes = Column(Integer, default=0)
    avg_comments = Column(Integer, default=0)
    posts_30d = Column(Integer, default=0)
    engagement_rate = Column(Float, default=0.0)

    grade = Column(String(10), nullable=True)
    score = Column(Float, nullable=True)
    decision = Column(String(20), nullable=True)
    tags = Column(JSON, default=list)
    risks = Column(JSON, default=list)

    brand_fit = Column(Float, default=0.0)
    reports_90d = Column(Integer, default=0)
    category = Column(String(100), nullable=True)


class CreatorHistoryTable(Base):
    """크리에이터 이력 SQLAlchemy 모델"""

    __tablename__ = "creator_history"

    id = Column(String(36), primary_key=True)
    creator_id = Column(String(100), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    change_type = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=False)

    previous_snapshot_id = Column(String(36), nullable=True)
    current_snapshot_id = Column(String(36), nullable=True)

    metrics_delta = Column(JSON, default=dict)

    mission_id = Column(String(36), nullable=True)
    mission_name = Column(String(200), nullable=True)


class CreatorHistoryService:
    """크리에이터 이력 추적 서비스"""

    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.DATABASE_URL

        # 인메모리 폴백
        if "sqlite" in self.database_url:
            self._use_memory = True
            self._snapshots: Dict[str, List[CreatorSnapshot]] = {}
            self._history: Dict[str, List[CreatorHistoryEntry]] = {}
        else:
            self._use_memory = False

        self._initialized = False

    async def initialize(self) -> None:
        """데이터베이스 초기화"""
        if self._initialized:
            return

        if not self._use_memory:
            try:
                sync_url = self.database_url.replace("+asyncpg", "")
                engine = create_engine(sync_url)
                Base.metadata.create_all(engine)
                engine.dispose()
                logger.info("Creator history tables created successfully")
            except Exception as e:
                logger.warning(
                    f"Failed to create creator history tables, falling back to memory: {e}"
                )
                self._use_memory = True
                self._snapshots = {}
                self._history = {}

        self._initialized = True

    async def record_evaluation(
        self,
        creator_id: str,
        platform: str,
        handle: str,
        metrics: Dict[str, Any],
        evaluation_result: Dict[str, Any],
    ) -> CreatorSnapshot:
        """크리에이터 평가 결과 기록"""
        await self.initialize()

        snapshot = CreatorSnapshot(
            id=str(uuid.uuid4()),
            creator_id=creator_id,
            timestamp=datetime.utcnow(),
            platform=platform,
            handle=handle,
            followers=metrics.get("followers", 0),
            avg_likes=metrics.get("avg_likes", 0),
            avg_comments=metrics.get("avg_comments", 0),
            posts_30d=metrics.get("posts_30d", 0),
            engagement_rate=metrics.get("engagement_rate", 0.0),
            grade=evaluation_result.get("grade"),
            score=evaluation_result.get("score"),
            decision=evaluation_result.get("decision"),
            tags=evaluation_result.get("tags", []),
            risks=evaluation_result.get("risks", []),
            brand_fit=metrics.get("brand_fit", 0.0),
            reports_90d=metrics.get("reports_90d", 0),
            category=metrics.get("category"),
        )

        previous_snapshot = await self._get_latest_snapshot(creator_id)
        metrics_delta: Dict[str, Any] = {}
        description = (
            f"평가 수행: {snapshot.grade} 등급, {snapshot.score:.1f}점"
            if snapshot.score
            else "평가 수행"
        )

        if previous_snapshot:
            metrics_delta = {
                "followers": snapshot.followers - previous_snapshot.followers,
                "engagement_rate": snapshot.engagement_rate
                - previous_snapshot.engagement_rate,
                "score": (snapshot.score or 0) - (previous_snapshot.score or 0),
            }
            if metrics_delta.get("score", 0) > 0:
                description += f" (점수 +{metrics_delta['score']:.1f})"

        history_entry = CreatorHistoryEntry(
            id=str(uuid.uuid4()),
            creator_id=creator_id,
            timestamp=snapshot.timestamp,
            change_type="evaluation",
            description=description,
            previous_snapshot_id=previous_snapshot.id if previous_snapshot else None,
            current_snapshot_id=snapshot.id,
            metrics_delta=metrics_delta,
        )

        await self._save_snapshot(snapshot)
        await self._save_history_entry(history_entry)

        logger.info(f"Recorded evaluation for creator {creator_id}: {snapshot.grade}")
        return snapshot

    async def record_mission_completion(
        self,
        creator_id: str,
        mission_id: str,
        mission_name: str,
        performance_metrics: Dict[str, Any] = None,
    ) -> CreatorHistoryEntry:
        """미션 완료 기록"""
        await self.initialize()

        history_entry = CreatorHistoryEntry(
            id=str(uuid.uuid4()),
            creator_id=creator_id,
            timestamp=datetime.utcnow(),
            change_type="mission_complete",
            description=f"미션 완료: {mission_name}",
            metrics_delta=performance_metrics or {},
            mission_id=mission_id,
            mission_name=mission_name,
        )

        await self._save_history_entry(history_entry)
        logger.info(
            f"Recorded mission completion for creator {creator_id}: {mission_name}"
        )
        return history_entry

    async def get_history(self, query: CreatorHistoryQuery) -> CreatorHistoryResponse:
        """크리에이터 이력 조회"""
        await self.initialize()
        if self._use_memory:
            return await self._get_history_memory(query)
        return await self._get_history_database(query)

    async def get_trend(
        self, creator_id: str, period_days: int = 30
    ) -> Optional[CreatorTrend]:
        """크리에이터 트렌드 분석"""
        await self.initialize()

        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=period_days)

        snapshots = await self._get_snapshots_in_range(creator_id, start_date, end_date)
        if len(snapshots) < 2:
            return None

        first = snapshots[0]
        last = snapshots[-1]

        followers_change = last.followers - first.followers
        followers_change_pct = (followers_change / max(first.followers, 1)) * 100

        engagement_change = last.engagement_rate - first.engagement_rate
        engagement_change_pct = (
            engagement_change / max(first.engagement_rate, 0.001)
        ) * 100

        score_change = None
        if first.score is not None and last.score is not None:
            score_change = last.score - first.score

        grade_improved = False
        grade_order = {"S": 4, "A": 3, "B": 2, "C": 1}
        if first.grade and last.grade:
            grade_improved = grade_order.get(last.grade, 0) > grade_order.get(
                first.grade, 0
            )

        history_entries = await self._get_history_in_range(
            creator_id, start_date, end_date
        )
        missions_completed = len(
            [e for e in history_entries if e.change_type == "mission_complete"]
        )

        if followers_change_pct > 5 and engagement_change > 0:
            trend_summary = "improving"
        elif followers_change_pct < -5 or engagement_change < -0.01:
            trend_summary = "declining"
        else:
            trend_summary = "stable"

        return CreatorTrend(
            creator_id=creator_id,
            period_start=start_date,
            period_end=end_date,
            followers_start=first.followers,
            followers_end=last.followers,
            followers_change=followers_change,
            followers_change_pct=followers_change_pct,
            engagement_start=first.engagement_rate,
            engagement_end=last.engagement_rate,
            engagement_change=engagement_change,
            engagement_change_pct=engagement_change_pct,
            score_start=first.score,
            score_end=last.score,
            score_change=score_change,
            grade_start=first.grade,
            grade_end=last.grade,
            grade_improved=grade_improved,
            missions_completed=missions_completed,
            trend_summary=trend_summary,
        )

    async def _get_latest_snapshot(self, creator_id: str) -> Optional[CreatorSnapshot]:
        """최신 스냅샷 조회"""
        if self._use_memory:
            snapshots = self._snapshots.get(creator_id, [])
            return snapshots[-1] if snapshots else None

        try:
            sync_url = self.database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                result = (
                    session.query(CreatorSnapshotTable)
                    .filter(CreatorSnapshotTable.creator_id == creator_id)
                    .order_by(CreatorSnapshotTable.timestamp.desc())
                    .first()
                )

                if result:
                    return CreatorSnapshot(
                        id=result.id,
                        creator_id=result.creator_id,
                        timestamp=result.timestamp,
                        platform=result.platform,
                        handle=result.handle,
                        followers=result.followers,
                        avg_likes=result.avg_likes,
                        avg_comments=result.avg_comments,
                        posts_30d=result.posts_30d,
                        engagement_rate=result.engagement_rate,
                        grade=result.grade,
                        score=result.score,
                        decision=result.decision,
                        tags=result.tags or [],
                        risks=result.risks or [],
                        brand_fit=result.brand_fit,
                        reports_90d=result.reports_90d,
                        category=result.category,
                    )
                return None
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            logger.error(f"Failed to get latest snapshot: {e}")
            return None

    async def _save_snapshot(self, snapshot: CreatorSnapshot) -> None:
        """스냅샷 저장"""
        if self._use_memory:
            if snapshot.creator_id not in self._snapshots:
                self._snapshots[snapshot.creator_id] = []
            self._snapshots[snapshot.creator_id].append(snapshot)
            return

        try:
            sync_url = self.database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                db_snapshot = CreatorSnapshotTable(
                    id=snapshot.id,
                    creator_id=snapshot.creator_id,
                    timestamp=snapshot.timestamp,
                    platform=snapshot.platform,
                    handle=snapshot.handle,
                    followers=snapshot.followers,
                    avg_likes=snapshot.avg_likes,
                    avg_comments=snapshot.avg_comments,
                    posts_30d=snapshot.posts_30d,
                    engagement_rate=snapshot.engagement_rate,
                    grade=snapshot.grade,
                    score=snapshot.score,
                    decision=snapshot.decision,
                    tags=snapshot.tags,
                    risks=snapshot.risks,
                    brand_fit=snapshot.brand_fit,
                    reports_90d=snapshot.reports_90d,
                    category=snapshot.category,
                )
                session.add(db_snapshot)
                session.commit()
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            logger.error(f"Failed to save snapshot: {e}")

    async def _save_history_entry(self, entry: CreatorHistoryEntry) -> None:
        """이력 항목 저장"""
        if self._use_memory:
            if entry.creator_id not in self._history:
                self._history[entry.creator_id] = []
            self._history[entry.creator_id].append(entry)
            return

        try:
            sync_url = self.database_url.replace("+asyncpg", "")
            engine = create_engine(sync_url)
            Session = sessionmaker(bind=engine)
            session = Session()

            try:
                db_entry = CreatorHistoryTable(
                    id=entry.id,
                    creator_id=entry.creator_id,
                    timestamp=entry.timestamp,
                    change_type=entry.change_type,
                    description=entry.description,
                    previous_snapshot_id=entry.previous_snapshot_id,
                    current_snapshot_id=entry.current_snapshot_id,
                    metrics_delta=entry.metrics_delta,
                    mission_id=entry.mission_id,
                    mission_name=entry.mission_name,
                )
                session.add(db_entry)
                session.commit()
            finally:
                session.close()
                engine.dispose()
        except Exception as e:
            logger.error(f"Failed to save history entry: {e}")

    async def _get_snapshots_in_range(
        self, creator_id: str, start_date: datetime, end_date: datetime
    ) -> List[CreatorSnapshot]:
        """기간 내 스냅샷 조회"""
        if self._use_memory:
            snapshots = self._snapshots.get(creator_id, [])
            return [s for s in snapshots if start_date <= s.timestamp <= end_date]
        # DB 조회 구현 (현재는 메모리 폴백)
        return []

    async def _get_history_in_range(
        self, creator_id: str, start_date: datetime, end_date: datetime
    ) -> List[CreatorHistoryEntry]:
        """기간 내 이력 조회"""
        if self._use_memory:
            history = self._history.get(creator_id, [])
            return [h for h in history if start_date <= h.timestamp <= end_date]
        return []

    async def _get_history_memory(
        self, query: CreatorHistoryQuery
    ) -> CreatorHistoryResponse:
        """메모리에서 이력 조회"""
        entries = self._history.get(query.creator_id, [])
        snapshots = self._snapshots.get(query.creator_id, [])

        if query.start_date:
            entries = [e for e in entries if e.timestamp >= query.start_date]
        if query.end_date:
            entries = [e for e in entries if e.timestamp <= query.end_date]
        if query.change_type:
            entries = [e for e in entries if e.change_type == query.change_type]

        entries.sort(key=lambda x: x.timestamp, reverse=True)
        total = len(entries)
        entries = entries[query.offset : query.offset + query.limit]

        trend = await self.get_trend(query.creator_id)

        return CreatorHistoryResponse(
            creator_id=query.creator_id,
            entries=entries,
            snapshots=snapshots[-10:],
            trend=trend,
            total=total,
        )

    async def _get_history_database(
        self, query: CreatorHistoryQuery
    ) -> CreatorHistoryResponse:
        """데이터베이스에서 이력 조회 (현재는 메모리 폴백)"""
        return await self._get_history_memory(query)


_creator_history_service: Optional[CreatorHistoryService] = None


def get_creator_history_service() -> CreatorHistoryService:
    """크리에이터 이력 서비스 인스턴스 반환"""
    global _creator_history_service
    if _creator_history_service is None:
        _creator_history_service = CreatorHistoryService()
    return _creator_history_service


__all__ = [
    "CreatorHistoryService",
    "CreatorSnapshotTable",
    "CreatorHistoryTable",
    "get_creator_history_service",
]
