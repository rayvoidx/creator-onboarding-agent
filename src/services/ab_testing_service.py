"""
Compatibility wrapper for A/B testing service.

Canonical implementation lives in `src.services.ab_testing.service`.
"""

from src.services.ab_testing.service import (  # noqa: F401
    ABTestingService,
    ExperimentStatus,
    Experiment,
    ExperimentResult,
    PromptVariant,
    VariantType,
    get_ab_testing_service,
)

__all__ = [
    "ABTestingService",
    "ExperimentStatus",
    "Experiment",
    "ExperimentResult",
    "PromptVariant",
    "VariantType",
    "get_ab_testing_service",
]
