"""
Compatibility wrapper for creator history service.

Canonical implementation lives in `src.services.creator_history.service`.
"""

from src.services.creator_history.service import (  # noqa: F401
    CreatorHistoryService,
    CreatorHistoryTable,
    CreatorSnapshotTable,
    get_creator_history_service,
)

__all__ = [
    "CreatorHistoryService",
    "CreatorSnapshotTable",
    "CreatorHistoryTable",
    "get_creator_history_service",
]
