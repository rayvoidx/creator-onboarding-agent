"""
Dependency injection container for the application.

Provides centralized access to shared application components.
"""

from typing import Optional

from src.graphs.main_orchestrator import MainOrchestrator
from src.rag.rag_pipeline import RAGPipeline
from src.agents.creator_onboarding_agent import CreatorOnboardingAgent

# Optional monitoring imports
try:
    from src.monitoring.performance_monitor import PerformanceMonitor
    from src.monitoring.metrics_collector import MetricsCollector
    MONITORING_AVAILABLE = True
except ImportError:
    PerformanceMonitor = None  # type: ignore
    MetricsCollector = None  # type: ignore
    MONITORING_AVAILABLE = False


class AppDependencies:
    """Application-wide dependency container."""

    def __init__(self):
        self.orchestrator: Optional[MainOrchestrator] = None
        self.rag_pipeline: Optional[RAGPipeline] = None
        self.performance_monitor: Optional["PerformanceMonitor"] = None
        self.metrics_collector: Optional["MetricsCollector"] = None
        self.creator_agent: Optional[CreatorOnboardingAgent] = None

    @property
    def monitoring_available(self) -> bool:
        return MONITORING_AVAILABLE


# Global singleton instance
_dependencies: Optional[AppDependencies] = None


def get_dependencies() -> AppDependencies:
    """Get the global dependencies container."""
    global _dependencies
    if _dependencies is None:
        _dependencies = AppDependencies()
    return _dependencies


def reset_dependencies() -> None:
    """Reset dependencies (primarily for testing)."""
    global _dependencies
    _dependencies = None
