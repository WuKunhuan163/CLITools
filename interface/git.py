"""Git integration interface.

Provides git hooks management and persistence operations.
"""
from logic.git.hooks import install_hooks, uninstall_hooks
from logic.git.persistence import get_persistence_manager
from logic.git.engine import auto_push_if_needed, auto_squash_if_needed, DEFAULT_SQUASH_CONFIG

__all__ = [
    "install_hooks",
    "uninstall_hooks",
    "get_persistence_manager",
    "auto_push_if_needed",
    "auto_squash_if_needed",
    "DEFAULT_SQUASH_CONFIG",
]
