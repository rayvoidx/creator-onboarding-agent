"""
Compatibility wrapper for settings.

Canonical settings module is `config.settings`.
`src.config.settings` is kept to avoid breaking imports in scripts and older modules.
"""

from config.settings import Settings, get_settings  # noqa: F401

__all__ = ["Settings", "get_settings"]
