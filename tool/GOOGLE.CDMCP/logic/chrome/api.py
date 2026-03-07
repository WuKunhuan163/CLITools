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

    Args:
        name: Session name.
        url: URL to open after the welcome page. If None, stays on welcome.
    """
    session_mgr = _load_mod("cdmcp_session_mgr", _SESSION_PATH)
    overlay = _load_mod("cdmcp_overlay", _OVERLAY_PATH)
    server_mod = _load_mod("cdmcp_server", _SERVER_PATH)

    server_url, _ = server_mod.start_server()

    session = session_mgr.create_session(name, timeout_sec=86400, port=port)
    sid_short = session.session_id[:8]
    created_ts = int(session.created_at) if hasattr(session, 'created_at') else int(time.time())
    idle_sec = getattr(session, 'timeout_sec', 3600)
    welcome_url = (
        f"{server_url}/welcome?session_id={sid_short}"
        f"&port={port}&timeout_sec=86400&created_at={created_ts}"
        f"&idle_timeout_sec={idle_sec}&last_activity={created_ts}"
    )
    boot_result = session.boot(welcome_url, new_window=True)

    if not boot_result.get("ok"):
        return boot_result

    time.sleep(0.8)
    cdp = session.get_cdp()

    if cdp:
        tab_id = session.lifetime_tab_id
        if tab_id:
            overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
            overlay.activate_tab(tab_id, port)
            session.register_tab("welcome", tab_id, url=welcome_url, state="active")
        overlay.inject_favicon(cdp, svg_color="#1a73e8", letter="C")
        overlay.inject_badge(cdp, text=f"CDMCP [{sid_short}]", color="#1a73e8")
        overlay.inject_focus(cdp, color="#1a73e8")

    if url:
        time.sleep(1.5)
        cdp = session.get_cdp()
        if cdp:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(2)
        session.lifetime_tab_url = url

    # Open the demo chat in a second tab within the same window (not pinned)
    time.sleep(0.5)
    chat_url = f"{server_url}/chat?session_id={sid_short}"
    demo_tab_id = session.open_tab_in_session(chat_url)
    demo_ws = None
    if demo_tab_id:
        time.sleep(1.5)
        from logic.chrome.session import list_tabs as _list_tabs
        for t in _list_tabs(port):
            if t.get("id") == demo_tab_id:
                ws = t.get("webSocketDebuggerUrl")
                if ws:
                    demo_ws = ws
                    session.register_tab("demo", demo_tab_id,
                                         url=chat_url, ws=ws, state="active")
                    demo_cdp = CDPSession(ws, timeout=10)
                    overlay.inject_favicon(demo_cdp, svg_color="#1a73e8", letter="C")
                    overlay.inject_badge(demo_cdp, text=f"Demo [{sid_short}]",
                                         color="#34a853")
                    demo_cdp.close()
                break

    # Start the continuous demo in a background subprocess
    if demo_ws:
        import subprocess, sys
        project_root = str(_TOOL_DIR.parent.parent)
        demo_py = str(_TOOL_DIR / "logic" / "cdp" / "demo.py")
        inline_code = (
            f"import sys, os; os.chdir({project_root!r}); "
            f"sys.path.insert(0, {project_root!r}); "
            "import importlib.util; "
            f"spec = importlib.util.spec_from_file_location('demo', {demo_py!r}); "
            "mod = importlib.util.module_from_spec(spec); "
            "spec.loader.exec_module(mod); "
            f"mod.run_demo_on_tab({demo_ws!r}, port={port})"
        )
        subprocess.Popen(
            [sys.executable, "-c", inline_code],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

    boot_result["session_id_short"] = sid_short
    return boot_result


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
