"""
Common domain models.

Base models and shared entities used across domains.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class BaseEntity(BaseModel):
    """Base entity with common fields."""

    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class AuditLog(BaseEntity):
    """Audit log entry."""

    user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    request_path: str
    request_method: str
    status_code: int
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    correlation_id: Optional[str] = None
    request_body: Optional[Dict[str, Any]] = None
    response_summary: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    duration_ms: Optional[float] = None


class User(BaseEntity):
    """User model for authentication."""

    username: str
    email: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    roles: list = Field(default_factory=list)
    permissions: list = Field(default_factory=list)
    last_login: Optional[datetime] = None
