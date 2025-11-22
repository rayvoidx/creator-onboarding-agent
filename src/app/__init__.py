"""
Application entry point module.

This module contains the FastAPI application setup, lifespan management,
and dependency injection configuration.
"""

from src.app.main import app, create_app

__all__ = ["app", "create_app"]
