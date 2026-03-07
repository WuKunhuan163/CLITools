"""MCP notebook helpers for GCS.

Previously managed .root.ipynb creation; now GCS uses any open Colab tab
(the default "Welcome to Colab" notebook is sufficient).  This module
retains the ``save_notebook_id`` entry point for backward compatibility but
the pre-flight/creation workflow has been removed.
"""
import json
import sys
from pathlib import Path


def _find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent.parent.parent.parent


_project_root = _find_project_root()
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
YELLOW = get_color("YELLOW")
RESET = get_color("RESET")


def run_mcp_create_notebook(as_json=False):
    """Deprecated. GCS no longer requires a dedicated notebook.

    Any Colab tab (including the default "Welcome to Colab") is sufficient.
    Use ``GCS --mcp boot`` to open a Colab tab.
    """
    if as_json:
        print(json.dumps({
            "status": "info",
            "message": "A dedicated notebook is no longer required. "
                       "Any open Colab tab works. Run GCS --mcp boot.",
        }))
    else:
        print(f"{BOLD}No dedicated notebook required{RESET}.")
        print(f"  GCS now works with any open Colab tab.")
        print(f"  Run {BOLD}GCS --mcp boot{RESET} to open a Colab tab.")
    return 0


def save_notebook_id(file_id):
    """Deprecated. Notebook ID is no longer stored in config."""
    print(f"{BOLD}{YELLOW}Deprecated{RESET}. GCS no longer tracks a specific notebook.")
    print(f"  Any open Colab tab is used automatically.")
    return 0
