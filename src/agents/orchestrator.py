"""
Legacy orchestrator module.

This file exists for backward compatibility. The canonical orchestrator lives in
`src.graphs.main_orchestrator` (LangGraph-based compound system).
"""

from __future__ import annotations

from src.graphs.main_orchestrator import MainOrchestrator, get_orchestrator

__all__ = [
    "MainOrchestrator",
    "get_orchestrator",
]


