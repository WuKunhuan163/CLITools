"""CDMCP endpoint handlers — structured JSON output for monitoring.

Provides ``CDMCP --endpoint <path>`` commands that return machine-readable
JSON, complementing the existing ``--mcp-*`` commands (human-readable).

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
"""

import json
import sys
from typing import List


def handle_cdmcp_endpoint(args: list) -> None:
    """Dispatch ``CDMCP --endpoint`` commands.

    Args:
        args: Arguments after ``--endpoint``.  Accepts slash-separated
              (``chrome/status``), space-separated (``chrome status``),
              or flag-separated (``--chrome --status``) forms.
    """
    segments = _parse_segments(args)

    if not segments:
        _print_help()
        return

    root = segments[0]

    STATIC_ROUTES = {
        ("chrome", "status"): _chrome_status,
        ("sessions",): _sessions,
        ("tabs",): _all_tabs,
        ("managed",): _managed_tabs,
        ("state",): _full_state,
        ("config",): _config,
        ("window",): _window_status,
    }

    key = tuple(segments)
    if key in STATIC_ROUTES:
        STATIC_ROUTES[key]()
        return

    if root == "session" and len(segments) >= 2:
        name = segments[1]
        sub = segments[2] if len(segments) >= 3 else "state"
        if sub == "state":
            _session_state(name)
        elif sub == "tabs":
            _session_tabs(name)
        else:
            _out({"ok": False, "error": f"Unknown session endpoint: {sub}"})
        return

    _out({"ok": False, "error": f"Unknown endpoint: {'/'.join(segments)}"})
    _print_help()


# ── Segment parser ────────────────────────────────────────────────────

def _parse_segments(args: list) -> List[str]:
    """Normalize args into flat path segments.

    Accepts:
        ["chrome/status"]           → ["chrome", "status"]
        ["chrome", "status"]        → ["chrome", "status"]
        ["--chrome", "--status"]    → ["chrome", "status"]
    """
    segments = []
    for arg in args:
        cleaned = arg.lstrip("-") if arg.startswith("--") else arg
        segments.extend(cleaned.split("/"))
    return [s for s in segments if s]


# ── Helpers ───────────────────────────────────────────────────────────

def _out(data: dict) -> None:
    def _default(obj):
        try:
            return str(obj)
        except Exception:
            return f"<{type(obj).__name__}>"
    print(json.dumps(data, indent=2, ensure_ascii=False, default=_default))


def _load_api():
    import importlib.util
    from pathlib import Path
    api_path = Path(__file__).resolve().parent / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("cdmcp_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Endpoint implementations ─────────────────────────────────────────

def _chrome_status():
    api = _load_api()
    _out(api.status())


def _sessions():
    api = _load_api()
    sessions = api.list_sessions()
    _out({"ok": True, "count": len(sessions), "sessions": sessions})


def _session_state(name: str):
    api = _load_api()
    session = api.get_session_by_name(name)
    if not session:
        _out({"ok": False, "error": f"Session '{name}' not found"})
        return

    info = {
        "ok": True,
        "name": name,
        "session_id": getattr(session, "session_id", "?"),
        "window_id": getattr(session, "window_id", None),
        "booted": getattr(session, "_booted", False),
    }

    lifetime_tab = getattr(session, "lifetime_tab_id", None)
    if lifetime_tab:
        info["lifetime_tab_id"] = lifetime_tab

    tabs = {}
    raw_tabs = getattr(session, "_tabs", {})
    for label, tinfo in raw_tabs.items():
        if isinstance(tinfo, dict):
            tabs[label] = {
                "id": tinfo.get("id", "?"),
                "url": tinfo.get("url", "?"),
                "alive": tinfo.get("alive", False),
            }
        else:
            tabs[label] = {"id": str(tinfo)}
    info["tabs"] = tabs

    _out(info)


def _session_tabs(name: str):
    api = _load_api()
    sessions = api.list_sessions()
    found = next((s for s in sessions if s["name"] == name), None)
    if not found:
        _out({"ok": False, "error": f"Session '{name}' not found"})
        return
    _out({
        "ok": True,
        "session": name,
        "session_id": found.get("session_id", "?"),
        "tabs": found.get("tabs", []),
    })


def _all_tabs():
    api = _load_api()
    from interface.chrome import list_tabs as chrome_list_tabs
    tabs = chrome_list_tabs()
    page_tabs = [
        {"id": t["id"], "url": t.get("url", ""), "title": t.get("title", ""),
         "type": t.get("type", "")}
        for t in tabs if t.get("type") == "page"
    ]
    _out({"ok": True, "count": len(page_tabs), "tabs": page_tabs})


def _managed_tabs():
    api = _load_api()
    raw = api.list_managed()
    tabs = []
    for t in raw:
        entry = {}
        for k, v in t.items():
            try:
                json.dumps(v)
                entry[k] = v
            except (TypeError, ValueError):
                entry[k] = str(v)
        tabs.append(entry)
    _out({"ok": True, "count": len(tabs), "tabs": tabs})


def _full_state():
    api = _load_api()
    from interface.chrome import list_tabs as chrome_list_tabs

    sessions = api.list_sessions()
    managed_raw = api.list_managed()
    chrome_tabs = chrome_list_tabs()
    page_tabs = [t for t in chrome_tabs if t.get("type") == "page"]

    managed = []
    for t in managed_raw:
        entry = {}
        for k, v in t.items():
            try:
                json.dumps(v)
                entry[k] = v
            except (TypeError, ValueError):
                entry[k] = str(v)
        managed.append(entry)

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

    _out({
        "ok": True,
        "active_session": active_name,
        "session_count": len(sessions),
        "sessions": sessions,
        "managed_tab_count": len(managed),
        "managed_tabs": managed,
        "chrome_page_tabs": len(page_tabs),
        "window": win,
    })


def _config():
    api = _load_api()
    cfg = api.get_config()
    _out({"ok": True, "config": cfg})


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
    elif isinstance(session, dict):
        clean["session"] = session
    if win.get("error"):
        clean["error"] = win["error"]
    _out(clean)


# ── Help ──────────────────────────────────────────────────────────────

def _print_help():
    print("""
CDMCP Endpoint Monitor (JSON output)

Usage: CDMCP --endpoint <path>

Endpoints:
  chrome/status              Chrome CDP availability and summary
  sessions                   List all CDMCP sessions
  session/<name>/state       Session detail (window, tabs, age)
  session/<name>/tabs        Tabs in a session
  tabs                       All Chrome page tabs
  managed                    Managed CDMCP tabs with focus/lock state
  state                      Full CDMCP state (sessions + tabs + window)
  config                     CDMCP configuration values
  window                     Session window status

Path formats (all equivalent):
  CDMCP --endpoint chrome/status
  CDMCP --endpoint chrome status
  CDMCP --endpoint --chrome --status
""".rstrip())
