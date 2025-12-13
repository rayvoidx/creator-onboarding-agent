"""
Core module.

Contains core abstractions, exceptions, and design patterns.
"""

from src.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseError,
    ExternalAPIError,
    NotFoundError,
    ValidationError,
)

__all__ = [
    "BaseError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ExternalAPIError",
]
