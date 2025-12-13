"""
데이터 수집 영속성 레이어

PostgreSQL 테이블 정의 및 데이터 액세스 레이어
"""

from datetime import datetime

from typing import Any

from sqlalchemy import JSON, Column, DateTime, Index, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base: Any = declarative_base()


class ContentMetadataTable(Base):
    """콘텐츠 메타데이터 SQLAlchemy 모델"""

    __tablename__ = "content_metadata"

    id = Column(String(255), primary_key=True)
    title = Column(String(500), nullable=False)
    content_type = Column(String(50), nullable=False, index=True)
    source = Column(String(50), nullable=False, index=True)
    url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    tags = Column(JSON, default=list)
    metadata_json = Column(JSON, default=dict)

    # 복합 인덱스
    __table_args__ = (
        Index("idx_source_type", "source", "content_type"),
        Index("idx_created_at_source", "created_at", "source"),
    )


class CollectionHistoryTable(Base):
    """수집 히스토리 SQLAlchemy 모델"""

    __tablename__ = "collection_history"

    id = Column(String(36), primary_key=True)
    source_type = Column(String(50), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, index=True)
    total_items = Column(String(10), default="0")
    success_count = Column(String(10), default="0")
    error_count = Column(String(10), default="0")
    error_details = Column(JSON, default=list)
    config = Column(JSON, default=dict)


class DataSourceConfigTable(Base):
    """데이터 소스 설정 SQLAlchemy 모델"""

    __tablename__ = "data_source_config"

    id = Column(String(36), primary_key=True)
    source_type = Column(String(50), nullable=False, unique=True)
    api_key_encrypted = Column(Text, nullable=True)  # 암호화된 API 키
    base_url = Column(String(500), nullable=False)
    collection_interval = Column(String(10), default="60")  # 분 단위
    max_items_per_request = Column(String(10), default="100")
    retry_count = Column(String(5), default="3")
    timeout = Column(String(10), default="30")
    is_active = Column(String(5), default="true")
    last_collected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
