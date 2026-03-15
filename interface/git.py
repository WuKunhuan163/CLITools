"""Git integration interface.

Provides git hooks management and persistence operations.
"""
from logic.git.hooks import install_hooks, uninstall_hooks
from logic.git.persistence import get_persistence_manager

__all__ = [
    "install_hooks",
    "uninstall_hooks",
    "get_persistence_manager",
]
