"""GOOGLE.CDMCP Tool Interface — Visual browser automation via Chrome CDP.

Provides functions for other tools to inject overlays, manage sessions,
lock tabs, and highlight elements in Chrome.

Since tool/GOOGLE.CDMCP/ has a dot in its name (not importable as a Python
package), consumer tools should use the loader helper::

    # In any tool that depends on GOOGLE.CDMCP:
    from logic.cdmcp_loader import load_cdmcp
    cdmcp = load_cdmcp()
    session = cdmcp.create_session("my_tool")
    session.boot("https://example.com")
    cdp = session.get_cdp()
    cdmcp.inject_badge(cdp, text="MyTool")

Or load specific modules directly::

    from logic.cdmcp_loader import load_cdmcp_overlay, load_cdmcp_sessions
    overlay = load_cdmcp_overlay()
    sessions = load_cdmcp_sessions()
"""

import importlib.util
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_PATH = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_SERVER_PATH = _TOOL_DIR / "logic" / "cdp" / "server.py"
_DEMO_PATH = _TOOL_DIR / "logic" / "cdp" / "demo.py"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_overlay():
    """Load the overlay module (badge, focus, lock, highlight)."""
    return _load_module("cdmcp_overlay", _OVERLAY_PATH)


def load_sessions():
    """Load the session manager module."""
    return _load_module("cdmcp_sessions", _SESSION_PATH)


def load_server():
    """Load the local HTTP server module."""
    return _load_module("cdmcp_server", _SERVER_PATH)


def load_demo():
    """Load the demo interaction module."""
    return _load_module("cdmcp_demo", _DEMO_PATH)
