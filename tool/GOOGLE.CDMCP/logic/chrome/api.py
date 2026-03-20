"""CDMCP High-Level API — Unified interface for browser automation with visual overlays.

Orchestrates tab management, overlay injection, element highlighting, and
privacy-aware navigation for agent-controlled Chrome sessions.
All overlay code lives inside this tool (not in root logic/).
"""

import json
import time
import datetime
import functools
import inspect
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List

from interface.chrome import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available, list_tabs, find_tab, real_click, capture_screenshot,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_PATH = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_SERVER_PATH = _TOOL_DIR / "logic" / "cdp" / "server.py"
_DEMO_PATH = _TOOL_DIR / "logic" / "cdp" / "demo.py"
_AUTH_PATH = _TOOL_DIR / "logic" / "cdp" / "google_auth.py"
_REPORT_DIR = _TOOL_DIR / "data" / "report"
_CONFIG_DIR = _TOOL_DIR / "data" / "config"
_CONFIG_FILE = _CONFIG_DIR / "cdmcp_config.json"


def _load_mod(name, path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_overlay = None
_session_mgr = None
_auth_mod = None


def _get_overlay():
    global _overlay
    if _overlay is None:
        _overlay = _load_mod("cdmcp_overlay", _OVERLAY_PATH)
    return _overlay


def _get_session_mgr():
    global _session_mgr
    if _session_mgr is None:
        _session_mgr = _load_mod("cdmcp_session_mgr", _SESSION_PATH)
    return _session_mgr


def _get_auth():
    global _auth_mod
    if _auth_mod is None:
        _auth_mod = _load_mod("cdmcp_google_auth", _AUTH_PATH)
    return _auth_mod


DEFAULT_CONFIG = {
    "allow_oauth_windows": True,
    "allow_navigation_outside_domain": True,
    "block_file_downloads": False,
    "screenshot_redact_sensitive": False,
    "log_interactions": True,
    "overlay_opacity": 0.08,
    "overlay_lock_flash_opacity": 0.25,
    "badge_text": "CDMCP",
    "badge_color": "#1a73e8",
    "focus_border_color": "#1a73e8",
    "highlight_color": "#e8710a",
    "auto_unlock_timeout_sec": 0,
    "session_default_timeout_sec": 86400,
}


def _load_config() -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE) as f:
                config.update(json.load(f))
        except (json.JSONDecodeError, OSError):
            pass
    return config


def _save_config(config: Dict[str, Any]) -> bool:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        merged = dict(DEFAULT_CONFIG)
        merged.update(config)
        with open(_CONFIG_FILE, "w") as f:
            json.dump(merged, f, indent=2)
        return True
    except OSError:
        return False


# In-memory tab tracking
_managed_tabs: Dict[str, Dict[str, Any]] = {}
_focused_tab_id: Optional[str] = None
_locked_tab_id: Optional[str] = None


def _log(action: str, detail: str = ""):
    cfg = _load_config()
    if not cfg.get("log_interactions", True):
        return
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = _REPORT_DIR / "interaction_log.txt"
    line = f"[{ts}] {action}"
    if detail:
        line += f" | {detail}"
    try:
        with open(log_file, "a") as f:
            f.write(line + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Session management (delegated)
# ---------------------------------------------------------------------------

def create_session(name: str, timeout_sec: int = None,
                   port: int = CDP_PORT) -> Any:
    cfg = _load_config()
    if timeout_sec is None:
        timeout_sec = cfg.get("session_default_timeout_sec", 86400)
    mgr = _get_session_mgr()
    return mgr.create_session(name, timeout_sec=timeout_sec, port=port)


def get_session_by_name(name: str):
    return _get_session_mgr().get_session(name)


def list_sessions() -> List[Dict[str, Any]]:
    return _get_session_mgr().list_sessions()


def close_session(name: str) -> bool:
    return _get_session_mgr().close_session(name)


def set_max_sessions(limit: int, policy: str = "fail"):
    """Configure max concurrent sessions.

    Args:
        limit: Max number (0 = unlimited).
        policy: "fail" | "kill_oldest_boot" | "kill_oldest_activity".
    """
    _get_session_mgr().set_max_sessions(limit, policy)


def get_max_sessions_config() -> Dict[str, Any]:
    return _get_session_mgr().get_max_sessions_config()


# ---------------------------------------------------------------------------
# Tab lifecycle
# ---------------------------------------------------------------------------

def ensure_session_window(port: int = CDP_PORT) -> Dict[str, Any]:
    """Verify the session window is alive; reboot if needed.

    All tab-related operations should call this as a prerequisite.
    Returns dict with 'ok', 'session', 'action' (alive/rebooted/failed).
    """
    sm = _get_session_mgr()
    if not sm:
        return {"ok": False, "error": "Session manager not available"}
    session = sm.get_any_active_session()
    if not session:
        boot_r = sm.boot_tool_session("default", timeout_sec=86400, port=port)
        if boot_r.get("ok"):
            return {"ok": True, "session": boot_r.get("session"), "action": "booted"}
        return {"ok": False, "error": "No session and boot failed"}
    if session.lifetime_tab_id:
        alive = any(
            t.get("id") == session.lifetime_tab_id
            for t in list_tabs(port)
        )
        if not alive:
            _log("ensure_session_window", "Window lost, rebooting...")
            rebooted = session.full_reboot()
            if rebooted:
                return {"ok": True, "session": session, "action": "rebooted"}
            return {"ok": False, "error": "Window lost and reboot failed"}
    return {"ok": True, "session": session, "action": "alive"}


# ---------------------------------------------------------------------------
# Unified prerequisite gate
# ---------------------------------------------------------------------------

def _check_cdp_prerequisites(port: int = CDP_PORT,
                             check_session: bool = True) -> Dict[str, Any]:
    """Three-stage prerequisite check for Chrome CDP operations.

    1. Chrome installed — attempt ``ensure_chrome()`` if CDP unreachable.
    2. CDP debug port responding — verify HTTP endpoint on *port*.
    3. Session window alive — call ``ensure_session_window()``
       (skipped when *check_session* is False).
    """
    if not is_chrome_cdp_available(port):
        sm = _get_session_mgr()
        if sm and hasattr(sm, "ensure_chrome"):
            r = sm.ensure_chrome()
            if not r.get("ok"):
                return {"ok": False, "step": "chrome_installed",
                        "error": "Chrome is not installed",
                        "hint": "Install Google Chrome or run: CDMCP --mcp-boot"}
            time.sleep(2)
            if not is_chrome_cdp_available(port):
                return {"ok": False, "step": "cdp_debug_mode",
                        "error": f"Chrome CDP not reachable on port {port}",
                        "hint": f"Launch Chrome with --remote-debugging-port={port}"}
        else:
            return {"ok": False, "step": "cdp_debug_mode",
                    "error": "Chrome CDP not available"}

    if check_session:
        win = ensure_session_window(port)
        if not win["ok"]:
            return {"ok": False, "step": "session_state",
                    "error": win.get("error", "Session check failed")}
        return {"ok": True, "action": win.get("action", "ready")}

    return {"ok": True, "action": "cdp_ready"}


def requires_cdp(check_session: bool = True):
    """Decorator that gates a function behind CDP prerequisites.

    Usage::

        @requires_cdp()                       # Chrome + CDP + session window
        def navigate(url, port=CDP_PORT): ...

        @requires_cdp(check_session=False)    # Chrome + CDP only
        def google_auth_status(port=CDP_PORT): ...

    The ``port`` argument is extracted from the wrapped function's
    signature automatically (falls back to ``CDP_PORT``).
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            sig = inspect.signature(fn)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            port = bound.arguments.get("port", CDP_PORT)
            check = _check_cdp_prerequisites(port, check_session=check_session)
            if not check["ok"]:
                return check
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@requires_cdp()
def navigate(url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    global _focused_tab_id
    _log("navigate", url)
    cfg = _load_config()
    ov = _get_overlay()

    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    tab = find_tab(domain, port=port)
    if tab:
        session = ov.get_session(tab)
        if session:
            try:
                session.evaluate(f"window.location.href = {json.dumps(url)}")
                time.sleep(1)
                ov.inject_all_overlays(
                    session, locked=False, focus=True,
                    badge_text=cfg.get("badge_text", "CDMCP"),
                    badge_color=cfg.get("badge_color", "#1a73e8"),
                    focus_color=cfg.get("focus_border_color", "#1a73e8"),
                )
                tid = tab.get("id", "")
                _managed_tabs[tid] = tab
                _focused_tab_id = tid
                return {"ok": True, "action": "reused", "tabId": tid, "url": url}
            finally:
                session.close()

    from interface.chrome import open_tab
    if open_tab(url, port):
        time.sleep(1)
        tab = find_tab(domain, port=port)
        if tab:
            session = ov.get_session(tab)
            if session:
                try:
                    ov.inject_all_overlays(
                        session, locked=False, focus=True,
                        badge_text=cfg.get("badge_text", "CDMCP"),
                        badge_color=cfg.get("badge_color", "#1a73e8"),
                        focus_color=cfg.get("focus_border_color", "#1a73e8"),
                    )
                    tid = tab.get("id", "")
                    _managed_tabs[tid] = tab
                    _focused_tab_id = tid
                    return {"ok": True, "action": "created", "tabId": tid, "url": url}
                finally:
                    session.close()
    return {"ok": False, "error": "Failed to open tab", "url": url}


@requires_cdp()
def focus_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    global _focused_tab_id
    _log("focus_tab", url_pattern)
    cfg = _load_config()
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        ov.inject_badge(session, text=cfg.get("badge_text", "CDMCP"),
                        color=cfg.get("badge_color", "#1a73e8"))
        ov.inject_focus(session, color=cfg.get("focus_border_color", "#1a73e8"))
        tid = tab.get("id", "")
        _managed_tabs[tid] = tab
        _focused_tab_id = tid
        return {"ok": True, "tabId": tid, "url": tab.get("url")}
    finally:
        session.close()


@requires_cdp()
def lock_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    global _locked_tab_id
    _log("lock_tab", url_pattern)
    cfg = _load_config()
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        ov.inject_lock(session,
                       base_opacity=cfg.get("overlay_opacity", 0.08),
                       flash_opacity=cfg.get("overlay_lock_flash_opacity", 0.25))
        _locked_tab_id = tab.get("id", "")
        return {"ok": True, "locked": True, "tabId": _locked_tab_id}
    finally:
        session.close()


@requires_cdp()
def unlock_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    global _locked_tab_id
    _log("unlock_tab", url_pattern)
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        ov.remove_lock(session)
        _locked_tab_id = None
        return {"ok": True, "locked": False, "tabId": tab.get("id")}
    finally:
        session.close()


@requires_cdp()
def highlight_element(url_pattern: str, selector: str,
                      label: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    _log("highlight_element", f"{url_pattern} | {selector} | {label}")
    cfg = _load_config()
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        return ov.inject_highlight(session, selector, label,
                                   color=cfg.get("highlight_color", "#e8710a"))
    finally:
        session.close()


@requires_cdp()
def clear_highlight(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        ov.remove_highlight(session)
        return {"ok": True}
    finally:
        session.close()


@requires_cdp()
def cleanup_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    global _focused_tab_id, _locked_tab_id
    _log("cleanup_tab", url_pattern)
    ov = _get_overlay()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = ov.get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        result = ov.remove_all_overlays(session)
        tid = tab.get("id", "")
        _managed_tabs.pop(tid, None)
        if _focused_tab_id == tid:
            _focused_tab_id = None
        if _locked_tab_id == tid:
            _locked_tab_id = None
        return {"ok": True, "removed": result.get("removed", [])}
    finally:
        session.close()


def boot_session(name: str = "default", url: str = None,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a named CDMCP session. Opens a welcome page in a new Chrome window.

    Delegates to session_manager.boot_tool_session which handles the full lifecycle:
    ensure Chrome -> create session -> welcome page -> pin -> overlays -> demo tab.

    Args:
        name: Session name.
        url: URL to open after the welcome page. If None, stays on welcome.
    """
    session_mgr = _load_mod("cdmcp_session_mgr", _SESSION_PATH)

    result = session_mgr.boot_tool_session(name, timeout_sec=86400, port=port)
    if not result.get("ok"):
        return result

    session = result.get("session")
    if url and session:
        time.sleep(1.5)
        cdp = session.get_cdp()
        if cdp:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(2)
        session.lifetime_tab_url = url

    result["session_id_short"] = session.session_id[:8] if session else ""
    return result


@requires_cdp()
def run_demo(port: int = CDP_PORT, delay: float = 1.2,
             continuous: bool = True) -> Dict[str, Any]:
    demo_mod = _load_mod("cdmcp_demo", _DEMO_PATH)
    return demo_mod.run_demo(port=port, delay=delay, continuous=continuous)


# ---------------------------------------------------------------------------
# Status & listing
# ---------------------------------------------------------------------------

def status(port: int = CDP_PORT) -> Dict[str, Any]:
    available = is_chrome_cdp_available(port)
    cfg = _load_config()
    sessions = list_sessions()
    return {
        "ok": True,
        "chrome_available": available,
        "managed_tabs": len(_managed_tabs),
        "focused_tab": _focused_tab_id,
        "locked_tab": _locked_tab_id,
        "sessions": len(sessions),
        "config": {
            "allow_oauth": cfg.get("allow_oauth_windows", True),
            "log_interactions": cfg.get("log_interactions", True),
        },
    }


def list_managed() -> List[Dict[str, Any]]:
    result = []
    for tid, tab in _managed_tabs.items():
        entry = dict(tab)
        entry["_cdmcp_focused"] = (tid == _focused_tab_id)
        entry["_cdmcp_locked"] = (tid == _locked_tab_id)
        result.append(entry)
    return result


def get_config() -> Dict[str, Any]:
    return _load_config()


def set_config_value(key: str, value: Any) -> bool:
    cfg = _load_config()
    cfg[key] = value
    return _save_config(cfg)


def reset_config() -> bool:
    return _save_config(DEFAULT_CONFIG)


def show_config_str() -> str:
    cfg = _load_config()
    privacy_docs = {
        "allow_oauth_windows": "Allow OAuth popup windows for developer efficiency.",
        "allow_navigation_outside_domain": "Allow agent to navigate outside the initial domain.",
        "block_file_downloads": "Block file downloads triggered by the agent.",
        "screenshot_redact_sensitive": "Redact sensitive fields in screenshots.",
        "log_interactions": "Log all agent interactions to report directory.",
        "overlay_opacity": "Base opacity for lock overlay (0.0 - 1.0).",
        "overlay_lock_flash_opacity": "Flash opacity on user click during lock.",
        "auto_unlock_timeout_sec": "Auto-unlock after N seconds (0 = never).",
        "session_default_timeout_sec": "Default session timeout (seconds, default 86400 = 24h).",
    }
    lines = []
    for key, val in sorted(cfg.items()):
        doc = privacy_docs.get(key, "")
        lines.append(f"  {key}: {json.dumps(val)}")
        if doc:
            lines.append(f"    # {doc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Google Account Auth API
# ---------------------------------------------------------------------------

@requires_cdp(check_session=False)
def google_auth_status(port: int = CDP_PORT, verify: bool = False) -> Dict[str, Any]:
    """Check current Google account login state.

    Returns cached state from the 1-second polling monitor. If the monitor
    isn't running yet, performs a one-shot cookie check.

    Set verify=True to validate cookies against Google's servers (slow, creates
    a temporary tab). Only needed after restoring saved cookies.
    """
    auth = _get_auth()
    state = auth.get_cached_auth_state()
    if state.get("last_checked", 0) > 0 and (state.get("email") or state.get("_probed")):
        return state

    result = {"signed_in": False, "email": None, "display_name": None}
    tabs = list_tabs(port)
    for t in tabs:
        ws = t.get("webSocketDebuggerUrl")
        if ws and t.get("type") == "page":
            try:
                cdp = CDPSession(ws, timeout=5)
                cookie_result = auth.check_auth_cookies(cdp, verify=verify)
                result["signed_in"] = cookie_result["signed_in"]
                result["email"] = cookie_result.get("email") or result["email"]
                result["display_name"] = (cookie_result.get("display_name")
                                          or result["display_name"])
                cdp.close()
                if result["signed_in"]:
                    break
            except Exception:
                continue

    result["last_checked"] = time.time()
    return result


def google_auth_ensure_monitor(session_name: str = "default"):
    """Ensure the auth monitor is running for the given session."""
    auth = _get_auth()
    session_mgr = _get_session_mgr()
    auth.start_auth_monitor(
        get_session_fn=lambda: session_mgr.get_session(session_name),
        interval=1.0
    )


def google_auth_on_change(callback):
    """Register a callback for auth state changes (signed_in toggles)."""
    auth = _get_auth()
    auth.on_auth_change(callback)


@requires_cdp(check_session=False)
def google_auth_login(session_name: str = "default",
                      tip_text: str = "Please sign in to your Google account below",
                      auto_close: bool = True,
                      start_tracker: bool = True) -> Dict[str, Any]:
    """Initiate Google login flow: open login tab, show tip, auto-close on success.

    Returns:
        Dict with 'status' ('opened', 'already_signed_in', 'login_in_progress', 'failed')
        and 'tab_id' if applicable.
    """
    auth = _get_auth()
    session_mgr = _get_session_mgr()
    session = session_mgr.get_session(session_name)
    if not session:
        return {"status": "failed", "error": "No active session"}
    return auth.initiate_login(session, tip_text=tip_text, auto_close=auto_close,
                               start_tracker=start_tracker)


@requires_cdp(check_session=False)
def google_auth_logout(session_name: str = "default",
                       auto_close: bool = True) -> Dict[str, Any]:
    """Initiate Google logout flow: open logout page, track, auto-close.

    Returns:
        Dict with 'status' and 'tab_id'.
    """
    auth = _get_auth()
    session_mgr = _get_session_mgr()
    session = session_mgr.get_session(session_name)
    if not session:
        return {"status": "failed", "error": "No active session"}
    return auth.initiate_logout(session, auto_close=auto_close)


# ── Tab Navigation by ID ────────────────────────────────────────────

@requires_cdp()
def navigate_tab(tab_id: str, url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate an existing tab (by target ID) to a new URL."""
    _log("navigate_tab", f"tab={tab_id[:12]} url={url}")
    tabs = list_tabs(port)
    target = next((t for t in tabs if t["id"] == tab_id and t.get("type") == "page"), None)
    if not target:
        return {"ok": False, "error": f"Tab not found: {tab_id[:12]}"}
    ws = target.get("webSocketDebuggerUrl")
    if not ws:
        return {"ok": False, "error": "No WebSocket URL for tab"}
    try:
        cdp = CDPSession(ws, timeout=15)
        cdp.send_and_recv("Page.navigate", {"url": url})
        time.sleep(2)
        title = cdp.evaluate("document.title") or ""
        cdp.close()
        return {"ok": True, "tabId": tab_id, "url": url, "title": title}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@requires_cdp()
def activate_tab(tab_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Bring a tab to the foreground (activate it in Chrome)."""
    _log("activate_tab", tab_id[:12])
    import urllib.request
    try:
        ver_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(ver_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return {"ok": False, "error": "No browser WS"}
        cdp = CDPSession(browser_ws, timeout=10)
        result = cdp.send_and_recv("Target.activateTarget", {"targetId": tab_id})
        cdp.close()
        if result and "error" not in result:
            return {"ok": True, "tabId": tab_id}
        return {"ok": False, "error": str(result.get("error", "unknown"))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Window Management ───────────────────────────────────────────────

@requires_cdp()
def minimize_window(port: int = CDP_PORT) -> Dict[str, Any]:
    """Minimize the current session's Chrome window."""
    _log("minimize_window", "")
    sm = _get_session_mgr()
    session = sm.get_any_active_session() if sm else None
    if not session or not session.window_id:
        return {"ok": False, "error": "No active session with window"}
    return _set_window_state(session.window_id, "minimized", port)


@requires_cdp()
def restore_window(port: int = CDP_PORT) -> Dict[str, Any]:
    """Restore (un-minimize) the current session's Chrome window."""
    _log("restore_window", "")
    sm = _get_session_mgr()
    session = sm.get_any_active_session() if sm else None
    if not session or not session.window_id:
        return {"ok": False, "error": "No active session with window"}
    return _set_window_state(session.window_id, "normal", port)


def _set_window_state(window_id: int, state: str, port: int = CDP_PORT) -> Dict[str, Any]:
    import urllib.request
    try:
        ver_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(ver_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return {"ok": False, "error": "No browser WS"}
        cdp = CDPSession(browser_ws, timeout=10)
        cdp.send_and_recv("Browser.setWindowBounds", {
            "windowId": window_id,
            "bounds": {"windowState": state}
        })
        cdp.close()
        return {"ok": True, "windowId": window_id, "state": state}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Screenshot ──────────────────────────────────────────────────────

def _resolve_tab(tab_id: Optional[str], port: int) -> Optional[Dict]:
    """Find a tab by explicit ID (full or prefix), or prefer the last focused/navigated tab."""
    tabs = list_tabs(port)
    page_tabs = [t for t in tabs if t.get("type") == "page"]
    if not page_tabs:
        return None
    if tab_id:
        exact = next((t for t in page_tabs if t["id"] == tab_id), None)
        if exact:
            return exact
        prefix_matches = [t for t in page_tabs if t["id"].startswith(tab_id)]
        return prefix_matches[0] if len(prefix_matches) == 1 else None
    if _focused_tab_id:
        match = next((t for t in page_tabs if t["id"] == _focused_tab_id), None)
        if match:
            return match
    sm = _get_session_mgr()
    session = sm.get_any_active_session() if sm else None
    if session and hasattr(session, "_tabs") and session._tabs:
        last_label = list(session._tabs.keys())[-1]
        last_info = session._tabs[last_label]
        last_id = last_info.get("id") if isinstance(last_info, dict) else None
        if last_id:
            match = next((t for t in page_tabs if t["id"] == last_id), None)
            if match:
                return match
    return page_tabs[-1]


@requires_cdp()
def screenshot_tab(tab_id: Optional[str] = None, output: str = "",
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Capture a screenshot of a tab. Default: last tab in current session."""
    _log("screenshot_tab", f"tab={tab_id or 'default'} output={output or 'auto'}")
    tab = _resolve_tab(tab_id, port)
    if not tab:
        return {"ok": False, "error": "No matching tab found"}
    ws = tab.get("webSocketDebuggerUrl")
    if not ws:
        return {"ok": False, "error": "No WebSocket URL for tab"}
    try:
        cdp = CDPSession(ws, timeout=15)
        _hide_overlays_js = """(function(){
            var ids = ['__cdmcp_lock_overlay__','__cdmcp_agent_badge__',
                       '__cdmcp_focus_border__','__cdmcp_element_highlight__',
                       '__cdmcp_tip_banner__','__cdmcp_lock_overlay___dot'];
            var hidden = [];
            ids.forEach(function(id){
                var el = document.getElementById(id);
                if(el && el.style.display !== 'none'){
                    hidden.push({id: id, prev: el.style.display});
                    el.style.display = 'none';
                }
            });
            window.__cdmcp_hidden_overlays__ = hidden;
            return hidden.length;
        })()"""
        _restore_overlays_js = """(function(){
            var hidden = window.__cdmcp_hidden_overlays__ || [];
            hidden.forEach(function(h){
                var el = document.getElementById(h.id);
                if(el) el.style.display = h.prev || '';
            });
            window.__cdmcp_hidden_overlays__ = null;
            return hidden.length;
        })()"""
        cdp.evaluate(_hide_overlays_js)
        img = capture_screenshot(cdp)
        cdp.evaluate(_restore_overlays_js)
        cdp.close()
        if not img:
            return {"ok": False, "error": "Screenshot returned empty"}
        if not output:
            _REPORT_DIR.mkdir(parents=True, exist_ok=True)
            output = str(_REPORT_DIR / "last_screenshot.png")
        from pathlib import Path as _P
        _P(output).parent.mkdir(parents=True, exist_ok=True)
        with open(output, "wb") as f:
            f.write(img)
        return {"ok": True, "path": output, "tabId": tab["id"],
                "size": len(img), "title": tab.get("title", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Element Focus ───────────────────────────────────────────────────

@requires_cdp()
def focus_element(url_pattern: str, selector: str,
                  port: int = CDP_PORT) -> Dict[str, Any]:
    """Focus a specific DOM element in a tab (sets document.activeElement)."""
    _log("focus_element", f"{url_pattern} | {selector}")
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    ws = tab.get("webSocketDebuggerUrl")
    if not ws:
        return {"ok": False, "error": "No WebSocket URL for tab"}
    try:
        cdp = CDPSession(ws, timeout=15)
        js = f'''(function(){{
            var el = document.querySelector({json.dumps(selector)});
            if (!el) return JSON.stringify({{"ok": false, "error": "Element not found"}});
            el.focus();
            el.scrollIntoView({{block: "center", behavior: "smooth"}});
            var r = el.getBoundingClientRect();
            return JSON.stringify({{
                "ok": true,
                "tag": el.tagName, "id": el.id || "",
                "text": (el.textContent || "").trim().substring(0, 80),
                "x": Math.round(r.x), "y": Math.round(r.y),
                "w": Math.round(r.width), "h": Math.round(r.height)
            }});
        }})()'''
        raw = cdp.evaluate(js)
        cdp.close()
        result = json.loads(raw) if raw else {"ok": False, "error": "Empty response"}
        if result.get("ok"):
            result["tabId"] = tab["id"]
            result["selector"] = selector
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Scroll ──────────────────────────────────────────────────────────

@requires_cdp()
def scroll_tab(url_pattern: str, dx: int = 0, dy: int = 0,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """Scroll within a tab. dx=horizontal pixels, dy=vertical pixels."""
    _log("scroll_tab", f"{url_pattern} dx={dx} dy={dy}")
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    ws = tab.get("webSocketDebuggerUrl")
    if not ws:
        return {"ok": False, "error": "No WebSocket URL for tab"}
    try:
        cdp = CDPSession(ws, timeout=15)
        vp_raw = cdp.evaluate(
            "JSON.stringify({w: window.innerWidth, h: window.innerHeight})")
        vp = json.loads(vp_raw) if vp_raw else {"w": 800, "h": 600}
        cx, cy = vp["w"] // 2, vp["h"] // 2
        cdp.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseWheel", "x": cx, "y": cy,
            "deltaX": dx, "deltaY": dy,
        }, timeout=5)
        time.sleep(0.3)
        pos_raw = cdp.evaluate(
            "JSON.stringify({x: window.scrollX, y: window.scrollY})")
        pos = json.loads(pos_raw) if pos_raw else {}
        cdp.close()
        return {"ok": True, "tabId": tab["id"],
                "scrollX": pos.get("x", 0), "scrollY": pos.get("y", 0),
                "deltaX": dx, "deltaY": dy}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ── Click Element ───────────────────────────────────────────────────

@requires_cdp()
def click_element(url_pattern: str, selector: str = "",
                  port: int = CDP_PORT) -> Dict[str, Any]:
    """Click an element. If selector is empty, clicks the currently focused element."""
    _log("click_element", f"{url_pattern} | {selector or '<focused>'}")
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    ws = tab.get("webSocketDebuggerUrl")
    if not ws:
        return {"ok": False, "error": "No WebSocket URL for tab"}
    try:
        cdp = CDPSession(ws, timeout=15)
        if selector:
            js = f'''(function(){{
                var el = document.querySelector({json.dumps(selector)});
                if (!el) return JSON.stringify({{"ok": false, "error": "Element not found"}});
                el.scrollIntoView({{block: "center"}});
                var r = el.getBoundingClientRect();
                return JSON.stringify({{
                    "ok": true, "x": r.x + r.width/2, "y": r.y + r.height/2,
                    "tag": el.tagName, "text": (el.textContent||"").trim().substring(0, 60)
                }});
            }})()'''
        else:
            js = '''(function(){
                var el = document.activeElement;
                if (!el || el === document.body)
                    return JSON.stringify({"ok": false, "error": "No focused element"});
                el.scrollIntoView({block: "center"});
                var r = el.getBoundingClientRect();
                return JSON.stringify({
                    "ok": true, "x": r.x + r.width/2, "y": r.y + r.height/2,
                    "tag": el.tagName, "text": (el.textContent||"").trim().substring(0, 60)
                });
            })()'''
        raw = cdp.evaluate(js)
        info = json.loads(raw) if raw else {"ok": False, "error": "Empty response"}
        if not info.get("ok"):
            cdp.close()
            return info
        x, y = info["x"], info["y"]
        real_click(cdp, x, y)
        time.sleep(0.3)
        cdp.close()
        return {"ok": True, "tabId": tab["id"],
                "clicked": {"x": round(x), "y": round(y),
                             "tag": info.get("tag", "?"),
                             "text": info.get("text", "")}}
    except Exception as e:
        return {"ok": False, "error": str(e)}
