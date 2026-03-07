"""CDMCP High-Level API — Unified interface for browser automation with visual overlays.

Orchestrates tab management, overlay injection, element highlighting, and
privacy-aware navigation for agent-controlled Chrome sessions.
All overlay code lives inside this tool (not in root logic/).
"""

import json
import time
import datetime
import importlib.util
from pathlib import Path
from typing import Optional, Dict, Any, List

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available, list_tabs, find_tab, close_tab,
    real_click, insert_text, dispatch_key,
    capture_screenshot, get_dom_text, get_dom_attribute,
    query_selector_all_text, fetch_api,
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

    from logic.chrome.session import open_tab
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

def google_auth_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check current Google account login state.

    Returns cached state from the 1-second polling monitor. If the monitor
    isn't running yet, performs a one-shot cookie check with identity probe.
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
                cookie_result = auth.check_auth_cookies(cdp)
                result["signed_in"] = cookie_result["signed_in"]
                cdp.close()
                if result["signed_in"]:
                    break
            except Exception:
                continue
    if not result["signed_in"]:
        return result

    for t in tabs:
        url = t.get("url") or ""
        ws = t.get("webSocketDebuggerUrl")
        if ws and t.get("type") == "page" and "google.com" in url:
            try:
                cdp = CDPSession(ws, timeout=5)
                body = cdp.evaluate(
                    "document.body ? document.body.innerText.substring(0, 3000) : ''"
                ) or ""
                import re
                m = re.search(r'[\w.+-]+@[\w.-]+\.[a-z]{2,}', body, re.I)
                if m:
                    result["email"] = m.group(0)
                cdp.close()
                if result["email"]:
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


def google_auth_login(session_name: str = "default",
                      tip_text: str = "Please sign in to your Google account below",
                      auto_close: bool = True) -> Dict[str, Any]:
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
    return auth.initiate_login(session, tip_text=tip_text, auto_close=auto_close)


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
