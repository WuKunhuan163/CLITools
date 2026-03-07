"""CDMCP Loader — Helper for tools that depend on GOOGLE.CDMCP.

Since tool/GOOGLE.CDMCP/ has a dot in its name and cannot be imported as a
Python package, this loader uses importlib to load modules from the tool
directory. Consumer tools should add "GOOGLE.CDMCP" to their dependencies
in tool.json and use this loader.

Usage::

    from logic.cdmcp_loader import load_cdmcp
    cdmcp = load_cdmcp()  # returns the interface module
    overlay = load_cdmcp_overlay()
    sessions = load_cdmcp_sessions()
"""

import importlib.util
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CDMCP_DIR = _PROJECT_ROOT / "tool" / "GOOGLE.CDMCP"
_INTERFACE_PATH = _CDMCP_DIR / "interface" / "main.py"
_OVERLAY_PATH = _CDMCP_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_PATH = _CDMCP_DIR / "logic" / "cdp" / "session_manager.py"
_SERVER_PATH = _CDMCP_DIR / "logic" / "cdp" / "server.py"
_INTERACT_PATH = _CDMCP_DIR / "logic" / "cdp" / "interact.py"
_DEMO_STATE_PATH = _CDMCP_DIR / "logic" / "cdp" / "demo_state.py"


def _load(name: str, path: Path):
    """Load a module by file path, caching in sys.modules for singleton behavior."""
    if name in sys.modules:
        return sys.modules[name]
    if not path.exists():
        raise ImportError(f"GOOGLE.CDMCP module not found: {path}")
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def load_cdmcp():
    """Load the CDMCP interface module."""
    return _load("cdmcp_interface", _INTERFACE_PATH)


def load_cdmcp_overlay():
    """Load the overlay module (badge, focus, lock, highlight)."""
    return _load("cdmcp_overlay", _OVERLAY_PATH)


def load_cdmcp_sessions():
    """Load the session manager module."""
    return _load("cdmcp_sessions", _SESSION_PATH)


def load_cdmcp_server():
    """Load the local HTTP server module."""
    return _load("cdmcp_server", _SERVER_PATH)


def load_cdmcp_interact():
    """Load the MCP interaction interfaces module."""
    return _load("cdmcp_interact", _INTERACT_PATH)


def load_cdmcp_demo_state():
    """Load the demo state machine module."""
    return _load("cdmcp_demo_state", _DEMO_STATE_PATH)
