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
_AUTH_PATH = _TOOL_DIR / "logic" / "cdp" / "google_auth.py"


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


def load_google_auth():
    """Load the Google auth monitoring module.

    Provides:
        - check_auth_cookies(cdp) -> dict: fast cookie-based auth check
        - check_auth_full(port) -> dict: full auth check with email/name
        - get_cached_auth_state() -> dict: cached state from monitor
        - start_auth_monitor(get_session_fn, interval) -> None
        - stop_auth_monitor() -> None
        - on_auth_change(callback) -> None: register state change callback
        - watch_tab_close(tab_id, on_close) -> None: tab close hook
    """
    return _load_module("cdmcp_google_auth", _AUTH_PATH)


_GLUE_PATH = _TOOL_DIR / "logic" / "cdp" / "glue_protocol.py"


def load_glue_protocol():
    """Load the glue protocol module for user action tracking.

    Provides:
        - UserActionTracker: Class to monitor tabs opened for manual user actions
        - track_user_action(session, url, ...) -> UserActionTracker: convenience
        - get_active_trackers() -> Dict: currently running trackers

    Default completion: fires when the user closes the tab.
    Override: pass is_complete=callable(ws, url) -> bool for custom detection
    (e.g., cookie check, redirect detection, CAPTCHA solve).
    """
    return _load_module("cdmcp_glue", _GLUE_PATH)


_MYACCOUNT_PATH = _TOOL_DIR / "logic" / "cdp" / "google_myaccount.py"


def load_google_myaccount():
    """Load the Google My Account automation module.

    Provides:
        - check_login_required(port) -> dict: check if signed in
        - get_profile(session, port) -> dict: name, email, phone, etc.
        - get_security_overview(session, port) -> dict: 2FA, devices
        - get_recent_activity(session, port) -> dict: recent logins
        - get_connected_apps(session, port) -> dict: third-party apps
        - get_devices(session, port) -> dict: signed-in devices
        - get_storage_usage(session, port) -> dict: Drive/Gmail storage
        - navigate_page(session, page, port) -> dict: navigate to sub-page
    """
    return _load_module("cdmcp_myaccount", _MYACCOUNT_PATH)
