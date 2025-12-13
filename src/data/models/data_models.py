"""Data collection models"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ContentType(str, Enum):
    """콘텐츠 타입"""

    DOCUMENT = "document"
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    INTERACTIVE = "interactive"
    OTHER = "other"


class CollectionStatus(str, Enum):
    """수집 상태"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class ContentMetadata(BaseModel):
    """콘텐츠 메타데이터"""

    id: str
    title: str
    content_type: ContentType
    source: str
    url: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tags: list[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        use_enum_values = True
