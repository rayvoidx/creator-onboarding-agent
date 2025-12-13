"""
Compatibility wrapper for circuit breaker pattern module.

Canonical implementation lives in `src.core.circuit_breaker`.
"""

from src.core.circuit_breaker import (  # noqa: F401
    CIRCUIT_BREAKER_CONFIGS,
    CircuitBreakerListener,
    CircuitBreakerManager,
    CircuitState,
    circuit_breaker,
    get_circuit_breaker_manager,
    init_circuit_breakers,
)

__all__ = [
    "CircuitState",
    "CircuitBreakerListener",
    "CircuitBreakerManager",
    "get_circuit_breaker_manager",
    "circuit_breaker",
    "CIRCUIT_BREAKER_CONFIGS",
    "init_circuit_breakers",
]
