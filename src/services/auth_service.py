"""
Compatibility wrapper for Auth service.

Canonical implementation lives in `src.services.auth.service`.
"""

from src.services.auth.service import (  # noqa: F401
    AuthService,
    get_auth_service,
)

__all__ = [
    "AuthService",
    "get_auth_service",
]
