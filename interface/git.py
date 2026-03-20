"""Git integration interface.

Provides git hooks management and persistence operations.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.git.hooks import install_hooks, uninstall_hooks
from logic._.git.persistence import get_persistence_manager
from logic._.git.engine import auto_push_if_needed, auto_squash_if_needed, DEFAULT_SQUASH_CONFIG

__all__ = [
    "install_hooks",
    "uninstall_hooks",
    "get_persistence_manager",
    "auto_push_if_needed",
    "auto_squash_if_needed",
    "DEFAULT_SQUASH_CONFIG",
]
