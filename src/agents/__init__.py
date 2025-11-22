"""
Agents module.

Contains all AI agents for the system, each with consistent structure:
- agent.py: Main agent implementation
- tools.py: Agent-specific tools
- prompts/: Prompt templates
"""

from src.agents.base import BaseAgent
from src.agents.orchestrator import MainOrchestrator, get_orchestrator

__all__ = [
    "BaseAgent",
    "MainOrchestrator",
    "get_orchestrator",
]
