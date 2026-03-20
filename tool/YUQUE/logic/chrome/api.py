"""ToS-restricted: YUQUE DOM automation disabled.

Use official API: https://www.yuque.com/yuque/developer
Only auth/session functions remain active.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from interface.chrome import CDPSession, CDP_PORT
from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
)

YUQUE_HOME = "https://www.yuque.com"
YUQUE_DASHBOARD = "https://www.yuque.com/dashboard"

_session_name = "yuque"
_yq_session = None
_yq_cdp: Optional[CDPSession] = None
_yq_tab_ws: Optional[str] = None


_TOS_ERR = ("Disabled: Use Yuque official API (yuque.com/yuque/developer) instead of DOM automation.")

_AUTH_FUNCS = frozenset({
    "boot_session", "get_session_status", "get_status", "get_auth_state",
    "get_page_info", "get_mcp_state", "take_screenshot",
})


def _tos_guard(func):
    """Decorator that blocks non-auth functions with ToS error."""
    import functools
    if func.__name__ in _AUTH_FUNCS or func.__name__.startswith("_"):
        return func

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return {"ok": False, "error": _TOS_ERR}
    return wrapper


def _debug_log(msg: str):
    """Write debug info to tmp/boot_debug.log."""
    log_dir = Path(__file__).resolve().parent.parent.parent / "tmp"
    log_dir.mkdir(exist_ok=True)
    with open(log_dir / "boot_debug.log", "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")


def _get_or_create_session(port: int = CDP_PORT):
    """Get or create a CDMCP session for Yuque."""
    global _yq_session
    sm = load_cdmcp_sessions()
    _debug_log(f"boot_tool_session('{_session_name}', port={port})")
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)
    _yq_session = boot_result["session"]
    _debug_log(f"session action={boot_result.get('action', '?')}")
    return _yq_session


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Return cached CDPSession or create a new one."""
    global _yq_cdp, _yq_tab_ws, _yq_session
    if _yq_session is None:
        _get_or_create_session(port)
    if _yq_session is None:
        return None

    tab_info = _yq_session.require_tab(
        _session_name,
        url_pattern="yuque.com",
        open_url=YUQUE_HOME,
        auto_open=True,
        wait_sec=10,
    )
    ws = tab_info.get("ws")
    if not ws:
        _debug_log("require_tab returned no ws")
        return None

    if _yq_cdp and _yq_tab_ws == ws:
        try:
            _yq_cdp.evaluate("1")
            return _yq_cdp
        except Exception:
            _debug_log("cached CDPSession stale, reconnecting")
            try:
                _yq_cdp.close()
            except Exception:
                pass

    if _yq_cdp:
        try:
            _yq_cdp.close()
        except Exception:
            pass

    _yq_cdp = CDPSession(ws)
    _yq_tab_ws = ws

    overlay = load_cdmcp_overlay()
    try:
        overlay.inject_badge(_yq_cdp, "Yuque MCP", color="#36ab60")
        overlay.inject_favicon(_yq_cdp, "Y", bg_color="#36ab60")
        overlay.inject_focus_indicator(_yq_cdp)
    except Exception:
        pass

    return _yq_cdp


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot the Yuque CDMCP session with retry logic."""
    sm = load_cdmcp_sessions()
    from interface.chrome import is_chrome_cdp_available

    for attempt in range(2):
        try:
            _debug_log(f"boot attempt {attempt + 1}")
            session = _get_or_create_session(port)
            if not session:
                raise RuntimeError("session is None")

            tab_info = session.require_tab(
                _session_name,
                url_pattern="yuque.com",
                open_url=YUQUE_HOME,
                auto_open=True,
                wait_sec=10,
            )
            ws = tab_info.get("ws")
            if not ws:
                raise RuntimeError("require_tab returned no ws")

            global _yq_cdp, _yq_tab_ws
            if _yq_cdp:
                try:
                    _yq_cdp.close()
                except Exception:
                    pass
            _yq_cdp = CDPSession(ws)
            _yq_tab_ws = ws

            overlay = load_cdmcp_overlay()
            try:
                overlay.inject_badge(_yq_cdp, "Yuque MCP", color="#36ab60")
                overlay.inject_favicon(_yq_cdp, "Y", bg_color="#36ab60")
                overlay.inject_focus_indicator(_yq_cdp)
            except Exception:
                pass

            url = _yq_cdp.evaluate("window.location.href") or ""
            action = tab_info.get("action", "opened")
            _debug_log(f"boot ok: url={url}, action={action}")
            return {"ok": True, "url": url, "action": action}

        except Exception as e:
            _debug_log(f"boot attempt {attempt + 1} failed: {e}")
            if attempt == 0:
                try:
                    sm.ensure_chrome(port)
                    time.sleep(2)
                    if not is_chrome_cdp_available(port):
                        _debug_log("CDP still unavailable after ensure_chrome")
                except Exception as e2:
                    _debug_log(f"ensure_chrome failed: {e2}")
            else:
                return {
                    "ok": False,
                    "error": str(e),
                    "hint": "Ensure Chrome is running with --remote-debugging-port=9222, or run 'CDMCP boot' first.",
                }


def get_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current page status."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var title = document.title || '';
                var url = window.location.href || '';
                var avatar = document.querySelector('.avatar, [class*="avatar"], img[alt*="头像"]');
                var loggedIn = !!avatar;
                return JSON.stringify({ok: true, title: title, url: url, logged_in: loggedIn});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get detailed page info: title, path, buttons, headings."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var title = document.title || '';
                var path = window.location.pathname || '';
                var buttons = [];
                var btns = document.querySelectorAll('button, [role="button"], a.ant-btn');
                for (var i = 0; i < Math.min(btns.length, 20); i++) {
                    var t = (btns[i].textContent || '').trim();
                    if (t.length > 0 && t.length < 50) buttons.push(t);
                }
                var headings = [];
                var hs = document.querySelectorAll('h1, h2, h3');
                for (var i = 0; i < Math.min(hs.length, 15); i++) {
                    var t = (hs[i].textContent || '').trim();
                    if (t.length > 0 && t.length < 80) headings.push(t);
                }
                return JSON.stringify({ok: true, title: title, path: path,
                                       buttons: buttons, headings: headings});
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def scan_elements(port: int = CDP_PORT) -> Dict[str, Any]:
    """Scan the current page for interactive elements."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var result = {ok: true, elements: []};
                var selectors = 'button, input, select, textarea, [role="button"], [role="tab"], ' +
                    '[role="menuitem"], .ant-btn, a[href], [contenteditable], ' +
                    '[role="checkbox"], [role="radio"], [role="switch"]';
                var els = document.querySelectorAll(selectors);
                for (var i = 0; i < Math.min(els.length, 60); i++) {
                    var el = els[i];
                    var rect = el.getBoundingClientRect();
                    if (rect.width === 0 && rect.height === 0) continue;
                    result.elements.push({
                        tag: el.tagName.toLowerCase(),
                        type: el.type || el.getAttribute('role') || '',
                        text: (el.textContent || el.value || '').trim().substring(0, 60),
                        className: (el.className || '').toString().substring(0, 80),
                        id: el.id || '',
                        rect: {x: Math.round(rect.x), y: Math.round(rect.y),
                               w: Math.round(rect.width), h: Math.round(rect.height)}
                    });
                }
                result.count = result.elements.length;
                return JSON.stringify(result);
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "Empty response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# Apply ToS guard to all public functions defined in this module
import types as _types
for _name in list(globals()):
    _obj = globals()[_name]
    if (isinstance(_obj, _types.FunctionType)
            and not _name.startswith("_")
            and getattr(_obj, "__module__", "") == __name__):
        globals()[_name] = _tos_guard(_obj)
del _types, _name, _obj
