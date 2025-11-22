"""
Configuration module.

Centralizes all application configuration management.
"""

from src.config.settings import Settings, get_settings
from src.config.constants import (
    APP_NAME,
    APP_VERSION,
    API_V1_PREFIX,
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
)

__all__ = [
    "Settings",
    "get_settings",
    "APP_NAME",
    "APP_VERSION",
    "API_V1_PREFIX",
    "DEFAULT_PAGE_SIZE",
    "MAX_PAGE_SIZE",
]
