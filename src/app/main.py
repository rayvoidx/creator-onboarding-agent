"""
FastAPI application factory and configuration.

This module creates and configures the FastAPI application with all
middleware, routes, and error handlers.
"""

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import get_settings
from src.api.middleware.audit import AuditMiddleware
from src.api.middleware.auth import AuthMiddleware
from src.api.middleware.correlation import CorrelationIdMiddleware
from src.api.middleware.error_handler import register_error_handlers
from src.api.middleware.rate_limit import RateLimitMiddleware
from src.api.routes.ab_testing_routes import router as ab_testing_router
from src.api.routes.audit_routes import router as audit_router

# Import routers
from src.api.routes.auth_routes import router as auth_router
from src.api.routes.creator_history_routes import router as creator_history_router
from src.api.routes.mcp_routes import router as mcp_router

# Import v1 API routes
from src.api.v1.routes import (
    analytics,
    circuit_breaker,
    competency,
    creator,
    health,
    llm,
    missions,
    monitoring,
    rag,
    recommendations,
    search,
    session,
)
from src.app.lifespan import lifespan
from src.monitoring.logging_setup import setup_logging

# Setup logging
setup_logging()

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    # Create FastAPI application
    application = FastAPI(
        title="AI Learning System API",
        description="LangGraph 기반 자체 학습형 하이브리드 AI 교육 솔루션",
        version="1.0.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # Configure middleware (order matters - last added = first executed)
    _configure_middleware(application, settings)

    # Register routers
    _register_routers(application)

    # Register error handlers
    register_error_handlers(application)

    # Configure static files for frontend (must be after API routes)
    _configure_static_files(application)

    return application


def _configure_middleware(app: FastAPI, settings) -> None:
    """Configure application middleware stack."""
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Correlation ID (should be near the top)
    app.add_middleware(CorrelationIdMiddleware)

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Authentication (optional)
    if settings.ENABLE_AUTH:
        app.add_middleware(AuthMiddleware, secret_key=settings.SECRET_KEY)

    # Rate limiting (optional)
    if settings.ENABLE_RATE_LIMITING:
        app.add_middleware(
            RateLimitMiddleware,
            enabled=settings.ENABLE_RATE_LIMITING,
            max_requests=100,
            window_seconds=60,
            redis_url=(settings.REDIS_URL if settings.RATE_LIMIT_USE_REDIS else None),
            use_redis=settings.RATE_LIMIT_USE_REDIS,
        )

    # Audit logging (after auth to capture user info)
    app.add_middleware(AuditMiddleware, enabled=True)


def _register_routers(app: FastAPI) -> None:
    """Register all API routers."""
    # Legacy routers (to be migrated to v1)
    app.include_router(auth_router)
    app.include_router(audit_router)
    app.include_router(creator_history_router)
    app.include_router(ab_testing_router)
    app.include_router(mcp_router)

    # v1 API routers
    app.include_router(health.router)
    app.include_router(competency.router)
    app.include_router(recommendations.router)
    app.include_router(search.router)
    app.include_router(analytics.router)
    app.include_router(llm.router)
    app.include_router(rag.router)
    app.include_router(creator.router)
    app.include_router(missions.router)
    app.include_router(monitoring.router)
    app.include_router(circuit_breaker.router)
    app.include_router(session.router)


def _configure_static_files(app: FastAPI) -> None:
    """Configure static file serving for frontend."""
    # Get the project root directory
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    frontend_dist = os.path.join(project_root, "frontend", "dist")

    if os.path.exists(frontend_dist):
        # Mount static assets (JS, CSS, images)
        assets_dir = os.path.join(frontend_dist, "assets")
        if os.path.exists(assets_dir):
            app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        # Serve index.html for SPA routing (catch-all route)
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            """Serve the SPA for all non-API routes."""
            # Don't serve index.html for API routes
            if full_path.startswith(
                ("api/", "docs", "redoc", "openapi.json", "health", "v1/")
            ):
                return None

            index_file = os.path.join(frontend_dist, "index.html")
            if os.path.exists(index_file):
                return FileResponse(index_file)
            return {"error": "Frontend not built"}

        logger.info(f"Frontend static files mounted from: {frontend_dist}")
    else:
        logger.warning(f"Frontend dist directory not found: {frontend_dist}")


# Create the application instance
app = create_app()


# Development server entry point
if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "src.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
