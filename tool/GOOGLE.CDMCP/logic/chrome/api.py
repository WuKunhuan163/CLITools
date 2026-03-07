"""CDMCP High-Level API — Unified interface for browser automation with visual overlays.

Orchestrates tab management, overlay injection, element highlighting, and
privacy-aware navigation for agent-controlled Chrome sessions.
"""

import json
import time
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available, list_tabs, find_tab, close_tab,
    real_click, insert_text, dispatch_key,
    capture_screenshot, get_dom_text, get_dom_attribute,
    query_selector_all_text, fetch_api,
)
from logic.cdp.overlay import (
    inject_badge, remove_badge,
    inject_focus, remove_focus,
    inject_lock, remove_lock, is_locked,
    inject_highlight, remove_highlight,
    inject_all_overlays, remove_all_overlays,
    get_session,
)

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_REPORT_DIR = _TOOL_DIR / "data" / "report"
_CONFIG_DIR = _TOOL_DIR / "data" / "config"
_CONFIG_FILE = _CONFIG_DIR / "cdmcp_config.json"

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


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

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
# Tab lifecycle
# ---------------------------------------------------------------------------

def navigate(url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open a URL in a managed CDMCP tab with badge and focus overlays."""
    global _focused_tab_id
    _log("navigate", url)
    cfg = _load_config()

    domain = url.split("//")[-1].split("/")[0] if "//" in url else url
    tab = find_tab(domain, port=port)
    if tab:
        session = get_session(tab)
        if session:
            try:
                session.evaluate(f"window.location.href = {json.dumps(url)}")
                time.sleep(1)
                inject_all_overlays(
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
            session = get_session(tab)
            if session:
                try:
                    inject_all_overlays(
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
    """Set focus on a tab matching url_pattern with overlay."""
    global _focused_tab_id
    _log("focus_tab", url_pattern)
    cfg = _load_config()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}

    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}

    try:
        inject_badge(session, text=cfg.get("badge_text", "CDMCP"),
                     color=cfg.get("badge_color", "#1a73e8"))
        inject_focus(session, color=cfg.get("focus_border_color", "#1a73e8"))
        tid = tab.get("id", "")
        _managed_tabs[tid] = tab
        _focused_tab_id = tid
        return {"ok": True, "tabId": tid, "url": tab.get("url")}
    finally:
        session.close()


def lock_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Lock a tab with overlay."""
    global _locked_tab_id
    _log("lock_tab", url_pattern)
    cfg = _load_config()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}

    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}

    try:
        inject_lock(session,
                    base_opacity=cfg.get("overlay_opacity", 0.08),
                    flash_opacity=cfg.get("overlay_lock_flash_opacity", 0.25))
        tid = tab.get("id", "")
        _locked_tab_id = tid
        return {"ok": True, "locked": True, "tabId": tid}
    finally:
        session.close()


def unlock_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Unlock a tab."""
    global _locked_tab_id
    _log("unlock_tab", url_pattern)
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}

    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}

    try:
        remove_lock(session)
        _locked_tab_id = None
        return {"ok": True, "locked": False, "tabId": tab.get("id")}
    finally:
        session.close()


def highlight_element(url_pattern: str, selector: str,
                      label: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Highlight an element by CSS selector on a matching tab."""
    _log("highlight_element", f"{url_pattern} | {selector} | {label}")
    cfg = _load_config()
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}

    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}

    try:
        return inject_highlight(session, selector, label,
                                color=cfg.get("highlight_color", "#e8710a"))
    finally:
        session.close()


def clear_highlight(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}
    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}
    try:
        remove_highlight(session)
        return {"ok": True}
    finally:
        session.close()


def cleanup_tab(url_pattern: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Remove all CDMCP overlays from a tab."""
    global _focused_tab_id, _locked_tab_id
    _log("cleanup_tab", url_pattern)
    tab = find_tab(url_pattern, port=port)
    if not tab:
        return {"ok": False, "error": f"Tab not found: {url_pattern}"}

    session = get_session(tab)
    if not session:
        return {"ok": False, "error": "Cannot connect to tab"}

    try:
        result = remove_all_overlays(session)
        tid = tab.get("id", "")
        _managed_tabs.pop(tid, None)
        if _focused_tab_id == tid:
            _focused_tab_id = None
        if _locked_tab_id == tid:
            _locked_tab_id = None
        return {"ok": True, "removed": result.get("removed", [])}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Status & listing
# ---------------------------------------------------------------------------

def status(port: int = CDP_PORT) -> Dict[str, Any]:
    available = is_chrome_cdp_available(port)
    cfg = _load_config()
    return {
        "ok": True,
        "chrome_available": available,
        "managed_tabs": len(_managed_tabs),
        "focused_tab": _focused_tab_id,
        "locked_tab": _locked_tab_id,
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


# ---------------------------------------------------------------------------
# Config helpers (exposed for CLI)
# ---------------------------------------------------------------------------

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
    }
    lines = []
    for key, val in sorted(cfg.items()):
        doc = privacy_docs.get(key, "")
        lines.append(f"  {key}: {json.dumps(val)}")
        if doc:
            lines.append(f"    # {doc}")
    return "\n".join(lines)
