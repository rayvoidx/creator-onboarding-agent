"""
Agents module.

Contains all AI agents for the system, each with consistent structure:
- agent.py: Main agent implementation
- tools.py: Agent-specific tools
- prompts/: Prompt templates
"""

from src.agents.deep_agents import DeepAgentsState, UnifiedDeepAgents

# Import sub-agents
from src.agents.integration_agent import IntegrationAgent, IntegrationState
from src.core.base import BaseAgent

# Lazy import orchestrator to avoid circular dependencies
try:
    from src.graphs.main_orchestrator import MainOrchestrator, get_orchestrator

    _ORCHESTRATOR_AVAILABLE = True
except ImportError as e:
    MainOrchestrator = None  # type: ignore
    get_orchestrator = None  # type: ignore
    _ORCHESTRATOR_AVAILABLE = False
    import logging

    logging.getLogger(__name__).warning(f"Orchestrator not available: {e}")

__all__ = [
    "BaseAgent",
    "MainOrchestrator",
    "get_orchestrator",
    "IntegrationAgent",
    "IntegrationState",
    "UnifiedDeepAgents",
    "DeepAgentsState",
]
