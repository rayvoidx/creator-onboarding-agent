"""Vector store"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def get_or_create_collection(
    client: Any, name: str, metadata: Optional[dict] = None
) -> Optional[Any]:
    """Get existing ChromaDB collection or create if missing.

    Returns None if client is falsy or operations fail.
    """
    if client is None:
        return None
    try:
        return client.get_collection(name)
    except Exception:
        try:
            return client.create_collection(name=name, metadata=metadata or {})
        except Exception as e:
            logger.error("Failed to get/create collection '%s': %s", name, e)
            return None
