"""Configuration interface for tools.

Provides access to color management, settings, global config, width checks,
and AI rule generation.
"""
from logic.config import get_color, get_setting, get_global_config
from logic.config.manager import print_width_check
from logic.config.main import set_global_config
from logic.config.rule.manager import generate_ai_rule, inject_rule

__all__ = [
    "get_color",
    "get_setting",
    "get_global_config",
    "set_global_config",
    "print_width_check",
    "generate_ai_rule",
    "inject_rule",
]
