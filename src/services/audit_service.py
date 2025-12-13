"""
Compatibility wrapper for Audit service.

Canonical implementation lives in `src.services.audit.service`.
"""

from src.services.audit.service import (  # noqa: F401
    AuditLogTable,
    AuditService,
    get_audit_service,
)

__all__ = [
    "AuditLogTable",
    "AuditService",
    "get_audit_service",
]
