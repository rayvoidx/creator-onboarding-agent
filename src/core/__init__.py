"""
Core module.

Contains core abstractions, exceptions, and design patterns.
"""

from src.core.exceptions import (
    BaseError,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ExternalAPIError,
)

__all__ = [
    "BaseError",
    "ValidationError",
    "AuthenticationError",
    "AuthorizationError",
    "NotFoundError",
    "ExternalAPIError",
]
