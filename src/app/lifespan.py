"""
Application lifespan management.

Handles startup and shutdown events for the FastAPI application.
"""

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from config.settings import get_settings
from src.agents.creator_onboarding_agent import CreatorOnboardingAgent
from src.app.dependencies import MONITORING_AVAILABLE, get_dependencies
from src.core.circuit_breaker import get_circuit_breaker_manager, init_circuit_breakers
from src.core.utils.agent_config import get_agent_runtime_config
from src.graphs.main_orchestrator import get_orchestrator
from src.monitoring.logging_setup import setup_logging
from src.rag.rag_pipeline import RAGPipeline

# Optional tracing imports
try:
    from src.monitoring.tracing import instrument_app, setup_tracing

    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False

# Optional monitoring imports
try:
    from src.monitoring.metrics_collector import MetricsCollector
    from src.monitoring.performance_monitor import PerformanceMonitor
except ImportError:
    PerformanceMonitor = None  # type: ignore
    MetricsCollector = None  # type: ignore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    deps = get_dependencies()
    settings = get_settings()

    # Startup
    logger.info("Starting AI Learning System API")
    try:
        # Initialize orchestrator
        deps.orchestrator = get_orchestrator(
            {
                "database_url": settings.DATABASE_URL,
                "redis_url": settings.REDIS_URL,
                "vector_db_config": settings.VECTOR_DB_CONFIG,
                "llm_configs": settings.LLM_CONFIGS,
            }
        )

        # Initialize RAG pipeline
        deps.rag_pipeline = RAGPipeline(
            {
                "retrieval": {
                    "vector_weight": 0.7,
                    "keyword_weight": 0.3,
                    "max_results": 10,
                },
                "generation": {
                    "default_model": settings.DEFAULT_LLM_MODEL,
                    "fallback_model": settings.FALLBACK_LLM_MODEL,
                    "openai_api_key": settings.OPENAI_API_KEY,
                    "anthropic_api_key": settings.ANTHROPIC_API_KEY,
                },
            }
        )

        # Initialize Creator Onboarding Agent
        deps.creator_agent = CreatorOnboardingAgent(get_agent_runtime_config("creator"))

        # Initialize Circuit Breakers
        init_circuit_breakers()
        # Ensure MCP tool circuit breakers exist so /api/v1/circuit-breaker/status shows them immediately
        try:
            cbm = get_circuit_breaker_manager()
            cbm.get_breaker(
                "mcp_web",
                fail_max=settings.MCP_WEB_FAIL_MAX,
                reset_timeout=settings.MCP_WEB_RESET_TIMEOUT_SECS,
            )
            cbm.get_breaker(
                "mcp_youtube",
                fail_max=settings.MCP_YOUTUBE_FAIL_MAX,
                reset_timeout=settings.MCP_YOUTUBE_RESET_TIMEOUT_SECS,
            )
            cbm.get_breaker(
                "mcp_supadata",
                fail_max=settings.MCP_SUPADATA_FAIL_MAX,
                reset_timeout=settings.MCP_SUPADATA_RESET_TIMEOUT_SECS,
            )
        except Exception as e:
            logger.warning("Failed to pre-initialize MCP circuit breakers: %s", e)
        logger.info("Circuit breakers initialized")

        # Initialize OpenTelemetry tracing (optional)
        if TRACING_AVAILABLE:
            try:
                otlp_endpoint = os.getenv("OTLP_ENDPOINT")
                setup_tracing(
                    service_name="creator-onboarding-agent",
                    otlp_endpoint=otlp_endpoint,
                    enable_console_export=settings.DEBUG,
                )
                instrument_app(app)
                logger.info("OpenTelemetry tracing initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize tracing: {e}")

        # Initialize monitoring systems (optional)
        if MONITORING_AVAILABLE and PerformanceMonitor and MetricsCollector:
            deps.performance_monitor = PerformanceMonitor(
                {
                    "latency_threshold": 5.0,
                    "error_rate_threshold": 0.1,
                    "max_history": 1000,
                }
            )

            deps.metrics_collector = MetricsCollector({"max_history": 1000})

            logger.info("Monitoring systems initialized")
        else:
            logger.warning(
                "Monitoring systems not available - install psutil for full monitoring"
            )

        logger.info("AI Chatbot Learning System API started successfully")

        yield

    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down AI Learning System API")
