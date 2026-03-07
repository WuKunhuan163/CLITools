"""Configuration interface for tools.

Provides access to color management, settings, and global config.
"""
from logic.config import get_color, get_setting, get_global_config

__all__ = [
    "get_color",
    "get_setting",
    "get_global_config",
]
