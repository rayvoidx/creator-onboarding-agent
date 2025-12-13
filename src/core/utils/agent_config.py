"""Utilities for agent-specific runtime configuration."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from config.settings import get_settings


def get_agent_runtime_config(
    agent_name: str,
    overrides: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Return merged configuration for the given agent.

    The base configuration comes from Settings.AGENT_MODEL_CONFIGS
    and can be overridden via the provided overrides dict.
    """
    settings = get_settings()
    base_config = deepcopy(settings.get_agent_config(agent_name))
    if overrides:
        base_config.update(overrides)
    return base_config


def attach_agent_config_to_context(
    context: Optional[Dict[str, Any]],
    agent_name: str,
) -> Dict[str, Any]:
    """Attach agent model config to the provided context copy."""
    ctx = dict(context or {})
    ctx["agent_model_config"] = get_settings().get_agent_config(agent_name)
    return ctx
