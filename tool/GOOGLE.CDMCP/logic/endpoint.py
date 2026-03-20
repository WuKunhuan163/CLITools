"""CDMCP endpoint handlers — structured JSON output for monitoring.

Uses ``interface.endpoint.EndpointRegistry`` for route dispatch.

Supported endpoints:
    chrome/status              Chrome CDP availability
    sessions                   List all CDMCP sessions
    session/<name>/state       Session detail (window, tabs, age)
    session/<name>/tabs        Tabs in a session
    tabs                       All Chrome page tabs
    managed                    Managed CDMCP tabs with focus/lock state
    state                      Full CDMCP state (sessions + tabs + window)
    config                     CDMCP configuration
    window                     Session window status
    urls                       Localhost URLs for all session pages
    url/<session>              URL for a specific session's welcome page
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from interface.endpoint import (
    EndpointRegistry, parse_endpoint_segments, _print_json,
)


def _load_api():
    import importlib.util
    api_path = Path(__file__).resolve().parent / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("cdmcp_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Registry setup ────────────────────────────────────────────────────

_registry = EndpointRegistry()


def _chrome_status():
    return _load_api().status()


def _sessions():
    api = _load_api()
    sessions = api.list_sessions()
    return {"ok": True, "count": len(sessions), "sessions": sessions}


def _all_tabs():
    from interface.chrome import list_tabs as chrome_list_tabs
    tabs = chrome_list_tabs()
    page_tabs = [
        {"id": t["id"], "url": t.get("url", ""), "title": t.get("title", ""),
         "type": t.get("type", "")}
        for t in tabs if t.get("type") == "page"
    ]
    return {"ok": True, "count": len(page_tabs), "tabs": page_tabs}


def _managed_tabs():
    api = _load_api()
    raw = api.list_managed()
    tabs = _safe_serialize_list(raw)
    return {"ok": True, "count": len(tabs), "tabs": tabs}


def _full_state():
    api = _load_api()
    from interface.chrome import list_tabs as chrome_list_tabs

    sessions = api.list_sessions()
    managed = _safe_serialize_list(api.list_managed())
    chrome_tabs = chrome_list_tabs()
    page_tabs = [t for t in chrome_tabs if t.get("type") == "page"]

    sm = api._get_session_mgr()
    active_name = None
    if sm:
        active = sm.get_any_active_session()
        if active:
            active_name = getattr(active, "_name", None) or getattr(active, "name", None)

    raw_win = api.ensure_session_window()
    win = {"ok": raw_win.get("ok", False), "action": raw_win.get("action", "?")}
    if raw_win.get("error"):
        win["error"] = raw_win["error"]

    return {
        "ok": True,
        "active_session": active_name,
        "session_count": len(sessions),
        "sessions": sessions,
        "managed_tab_count": len(managed),
        "managed_tabs": managed,
        "chrome_page_tabs": len(page_tabs),
        "window": win,
    }


def _config():
    return {"ok": True, "config": _load_api().get_config()}


def _window_status():
    api = _load_api()
    win = api.ensure_session_window()
    clean = {
        "ok": win.get("ok", False),
        "action": win.get("action", win.get("error", "unknown")),
    }
    session = win.get("session")
    if session and hasattr(session, "window_id"):
        clean["window_id"] = session.window_id
        clean["session_name"] = getattr(session, "_name", None) or getattr(session, "name", "?")
    if win.get("error"):
        clean["error"] = win["error"]
    return clean


def _urls():
    """Return localhost URLs for all session welcome pages."""
    api = _load_api()
    sessions = api.list_sessions()
    urls = []
    for s in sessions:
        sid = s.get("session_id", "?")
        port = s.get("http_port")
        if port:
            url = f"http://127.0.0.1:{port}/welcome?session_id={sid}"
        else:
            url = s.get("lifetime_tab_url", "")
        urls.append({
            "session": s.get("name", "?"),
            "session_id": sid,
            "welcome_url": url,
            "http_port": port,
        })
    return {"ok": True, "urls": urls}


def _session_handler(*segments):
    """Dynamic handler for session/<name>/..."""
    if not segments:
        return {"ok": False, "error": "Missing session name"}

    name = segments[0]
    sub = segments[1] if len(segments) >= 2 else "state"

    api = _load_api()

    if sub == "state":
        session = api.get_session_by_name(name)
        if not session:
            return {"ok": False, "error": f"Session '{name}' not found"}
        info = {
            "ok": True,
            "name": name,
            "session_id": getattr(session, "session_id", "?"),
            "window_id": getattr(session, "window_id", None),
            "booted": getattr(session, "_booted", False),
        }
        lt = getattr(session, "lifetime_tab_id", None)
        if lt:
            info["lifetime_tab_id"] = lt
        tabs = {}
        for label, tinfo in getattr(session, "_tabs", {}).items():
            if isinstance(tinfo, dict):
                tabs[label] = {
                    "id": tinfo.get("id", "?"),
                    "url": tinfo.get("url", "?"),
                    "alive": tinfo.get("alive", False),
                }
            else:
                tabs[label] = {"id": str(tinfo)}
        info["tabs"] = tabs
        port = getattr(session, "_http_port", None)
        if port:
            info["welcome_url"] = f"http://127.0.0.1:{port}/welcome?session_id={info['session_id']}"
        return info

    elif sub == "tabs":
        sessions = api.list_sessions()
        found = next((s for s in sessions if s["name"] == name), None)
        if not found:
            return {"ok": False, "error": f"Session '{name}' not found"}
        return {
            "ok": True,
            "session": name,
            "session_id": found.get("session_id", "?"),
            "tabs": found.get("tabs", []),
        }

    elif sub == "url":
        session = api.get_session_by_name(name)
        if not session:
            return {"ok": False, "error": f"Session '{name}' not found"}
        port = getattr(session, "_http_port", None)
        sid = getattr(session, "session_id", "?")
        if port:
            url = f"http://127.0.0.1:{port}/welcome?session_id={sid}"
        else:
            url = getattr(session, "lifetime_tab_url", "")
        return {"ok": True, "session": name, "url": url}

    return {"ok": False, "error": f"Unknown session endpoint: {sub}"}


def _url_handler(*segments):
    """Dynamic handler for url/<session_name>."""
    if not segments:
        return _urls()
    return _session_handler(segments[0], "url")


# Register all routes
_registry.register("chrome/status", _chrome_status, doc="Chrome CDP availability")
_registry.register("sessions", _sessions, doc="List all CDMCP sessions")
_registry.register("tabs", _all_tabs, doc="All Chrome page tabs")
_registry.register("managed", _managed_tabs, doc="Managed CDMCP tabs (focus/lock)")
_registry.register("state", _full_state, doc="Full CDMCP state")
_registry.register("config", _config, doc="CDMCP configuration")
_registry.register("window", _window_status, doc="Session window status")
_registry.register("urls", _urls, doc="Localhost URLs for session pages")
_registry.register_dynamic("session", _session_handler, doc="Session detail/tabs/url")
_registry.register_dynamic("url", _url_handler, doc="URL for session welcome page")


# ── Helpers ───────────────────────────────────────────────────────────

def _safe_serialize_list(items):
    result = []
    for t in items:
        entry = {}
        for k, v in t.items():
            try:
                json.dumps(v)
                entry[k] = v
            except (TypeError, ValueError):
                entry[k] = str(v)
        result.append(entry)
    return result


# ── Public entry point ────────────────────────────────────────────────

def handle_cdmcp_endpoint(args: list) -> None:
    """Dispatch ``CDMCP --endpoint`` commands."""
    segments = parse_endpoint_segments(args)

    if not segments:
        print(_registry.help_text("CDMCP"))
        return

    if not _registry.dispatch(segments):
        _print_json({"ok": False, "error": f"Unknown endpoint: {'/'.join(segments)}"})
        print(_registry.help_text("CDMCP"))
