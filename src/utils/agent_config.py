"""
Compatibility wrapper for agent config utilities.

Canonical implementation lives in `src.core.utils.agent_config`.
"""

from src.core.utils.agent_config import (  # noqa: F401
    attach_agent_config_to_context,
    get_agent_runtime_config,
)

__all__ = [
    "get_agent_runtime_config",
    "attach_agent_config_to_context",
]
