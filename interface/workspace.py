"""Workspace interface: mount, manage, and query external directories.

Usage:
    from interface.workspace import get_workspace_manager

    wm = get_workspace_manager()
    info = wm.create_workspace("/path/to/my/project")
    wm.open_workspace(info["id"])
    wm.close_workspace()
"""
from pathlib import Path
from typing import Dict, List, Optional

_ROOT = Path(__file__).resolve().parent.parent


def get_workspace_manager(root: Optional[Path] = None):
    """Get the workspace manager instance."""
    from logic._.workspace.manager import WorkspaceManager
    return WorkspaceManager(root or _ROOT)


__all__ = ["get_workspace_manager"]
