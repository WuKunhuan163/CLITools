"""Path resolution interface.

Provides setup_paths for bootstrapping import paths in tool entry points.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from logic._.utils.resolve import setup_paths

__all__ = [
    "setup_paths",
]
