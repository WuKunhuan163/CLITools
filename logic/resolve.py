"""Backward-compatible shim — resolve has moved to logic/utils/resolve."""
from logic.utils.resolve import *  # noqa: F401,F403
from logic.utils.resolve import find_project_root, setup_paths, get_tool_module_path
