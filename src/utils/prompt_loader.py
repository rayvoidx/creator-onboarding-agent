"""
Compatibility wrapper for prompt loader utilities.

Canonical implementation lives in `src.core.utils.prompt_loader`.
"""

from src.core.utils.prompt_loader import PromptLoader, get_prompt_loader  # noqa: F401

__all__ = [
    "PromptLoader",
    "get_prompt_loader",
]
