"""Tool interface registry — discover and load tool interfaces dynamically.

Follows the symmetrical design pattern: each tool at tool/<NAME>/interface/main.py
exposes functions for cross-tool communication. This registry provides a central
way to access those interfaces from any part of the codebase.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TOOL_DIR = _PROJECT_ROOT / "tool"
_cache: dict = {}


def get_interface(tool_name: str) -> Optional[ModuleType]:
    """Load and return a tool's interface module, or None if unavailable.

    Args:
        tool_name: The tool name (e.g. "TAVILY", "GIT", "iCloud").
                   Supports dotted names (e.g. "iCloud.iCloudPD").

    Returns:
        The tool's interface module (tool.<NAME>.interface.main),
        or None if the tool is not installed or has no interface.
    """
    if tool_name in _cache:
        return _cache[tool_name]

    interface_path = _TOOL_DIR / tool_name / "interface" / "main.py"
    if not interface_path.exists():
        _cache[tool_name] = None
        return None

    module_name = f"tool.{tool_name}.interface.main"
    project_root_str = str(_PROJECT_ROOT)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)

    try:
        mod = importlib.import_module(module_name)
        _cache[tool_name] = mod
        return mod
    except Exception:
        _cache[tool_name] = None
        return None


def list_interfaces() -> List[str]:
    """Return names of all tools that expose an interface module."""
    if not _TOOL_DIR.exists():
        return []
    result = []
    for tool_dir in sorted(_TOOL_DIR.iterdir()):
        if not tool_dir.is_dir():
            continue
        interface_file = tool_dir / "interface" / "main.py"
        if interface_file.exists():
            result.append(tool_dir.name)
    return result
