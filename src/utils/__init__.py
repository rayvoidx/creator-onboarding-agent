"""
`src.utils` package (compatibility layer).

Canonical utilities live in `src.core.utils`.
"""

from src.core.utils.agent_config import get_agent_runtime_config, attach_agent_config_to_context
from src.core.utils.prompt_loader import PromptLoader, get_prompt_loader

__all__ = [
    "get_agent_runtime_config",
    "attach_agent_config_to_context",
    "PromptLoader",
    "get_prompt_loader",
]


