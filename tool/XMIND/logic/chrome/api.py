"""XMind operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP sessions to manage the app.xmind.com browser tab with
visual overlays, state machine tracking, and MCP interaction interfaces.
"""

import json
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

from tool.XMIND.logic.chrome.state_machine import (
    XMState, get_machine, XMindStateMachine,
)

XMIND_HOME = "https://app.xmind.com"
_session_name = "xmind"

_CDMCP_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "GOOGLE.CDMCP"
_OVERLAY_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_INTERACT_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "interact.py"

_xm_session = None


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_overlay():
    return _load_module("cdmcp_overlay", _OVERLAY_PATH)


def _load_session_mgr():
    return _load_module("cdmcp_session_mgr", _SESSION_MGR_PATH)


def _load_interact():
    return _load_module("cdmcp_interact", _INTERACT_PATH)


def _get_or_create_session(port: int = CDP_PORT):
    global _xm_session
    if _xm_session is not None:
        cdp = _xm_session.get_cdp()
        if cdp:
            return _xm_session
        _xm_session = None

    sm = _load_session_mgr()
    existing = sm.get_session(_session_name)
    if existing:
        cdp = existing.get_cdp()
        if cdp:
            _xm_session = existing
            return existing
        sm.close_session(_session_name)
    return None


def _reapply_overlays(cdp, session, port):
    overlay = _load_overlay()
    tab_id = session.lifetime_tab_id
    if tab_id:
        overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
        overlay.activate_tab(tab_id, port)
    overlay.inject_favicon(cdp, svg_color="#f44336", letter="X")
    overlay.inject_badge(cdp, text="XMind MCP", color="#f44336")
    overlay.inject_focus(cdp, color="#f44336")


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a new XMind CDMCP session in a dedicated window."""
    global _xm_session
    machine = get_machine(_session_name)
    sm = _load_session_mgr()
    overlay = _load_overlay()

    if machine.state not in (XMState.UNINITIALIZED, XMState.ERROR):
        existing = _get_or_create_session(port)
        if existing:
            return {"ok": True, "action": "already_booted", **machine.to_dict()}

    if machine.state == XMState.ERROR:
        machine.transition(XMState.RECOVERING)
        if not machine.can_recover():
            machine.reset()
        machine.transition(XMState.UNINITIALIZED)

    machine.transition(XMState.BOOTING, {"url": XMIND_HOME})

    # Show welcome page first
    server_path = _CDMCP_TOOL_DIR / "logic" / "cdp" / "server.py"
    server_mod = _load_module("cdmcp_server", server_path)
    server_url, _ = server_mod.start_server()
    welcome_url = f"{server_url}/welcome?session=xmind&tool=XMind&letter=X&timeout=24h"

    session = sm.create_session(_session_name, timeout_sec=86400, port=port)
    boot_result = session.boot(welcome_url, new_window=True)

    if not boot_result.get("ok"):
        machine.transition(XMState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _xm_session = session
    time.sleep(0.8)

    cdp = session.get_cdp()
    if cdp:
        _reapply_overlays(cdp, session, port)

    # Navigate to XMind after showing welcome
    time.sleep(2)
    cdp = session.get_cdp()
    if cdp:
        cdp.evaluate(f"window.location.href = {json.dumps(XMIND_HOME)}")
        for _ in range(10):
            time.sleep(1)
            cur = cdp.evaluate("window.location.href") or ""
            if "xmind" in str(cur).lower():
                break

    session.lifetime_tab_url = XMIND_HOME
    machine.transition(XMState.IDLE)
    machine.set_url(XMIND_HOME)

    return {"ok": True, "action": "booted", **machine.to_dict(), **boot_result}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get an active CDP session, booting if needed."""
    global _xm_session
    machine = get_machine(_session_name)

    session = _get_or_create_session(port)
    if session:
        cdp = session.get_cdp()
        if cdp:
            if session.tab_was_recovered:
                _reapply_overlays(cdp, session, port)
                session.tab_was_recovered = False
            return cdp

    if machine.state == XMState.UNINITIALIZED:
        r = boot_session(port)
        if r.get("ok"):
            session = _get_or_create_session(port)
            if session:
                return session.get_cdp()

    if machine.state == XMState.ERROR:
        return _recover(port)

    return None


def _recover(port: int = CDP_PORT) -> Optional[CDPSession]:
    machine = get_machine(_session_name)
    if not machine.can_recover():
        machine.reset()
        return None

    machine.transition(XMState.RECOVERING)
    r = boot_session(port)
    if not r.get("ok"):
        return None

    target = machine.get_recovery_target()
    url = target.get("url", XMIND_HOME)
    session = _get_or_create_session(port)
    if session:
        cdp = session.get_cdp()
        if cdp and url != XMIND_HOME:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(3)
        return cdp
    return None


# ----- Public API -----

def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check XMind authentication state."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "authenticated": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var isLogin = url.includes("/login") || url.includes("/signin");
                var isHome = url.includes("/home") || url.includes("/recents");
                return JSON.stringify({
                    ok: true, url: url, title: title,
                    isLogin: isLogin,
                    authenticated: isHome && !isLogin
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current XMind page info."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title,
                    section: window.location.pathname.split('/').filter(Boolean).pop() || 'home'
                });
            })()
        """)
        result = json.loads(r) if r else {"ok": False}
        machine = get_machine(_session_name)
        url = result.get("url", "")
        machine.set_url(url)
        if "/recents" in url or "/home" in url:
            if machine.state not in (XMState.VIEWING_HOME,):
                machine.transition(XMState.VIEWING_HOME, {"url": url})
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_maps(port: int = CDP_PORT) -> Dict[str, Any]:
    """List mind maps visible on the current page."""
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        machine.transition(XMState.NAVIGATING, {"action": "list_maps"})
        r = cdp.evaluate("""
            (function() {
                try {
                    var cards = document.querySelectorAll(
                        "[class*=file-card], [class*=FileCard], [class*=map-card], " +
                        "[class*=MapCard], [class*=card-item], [class*=CardItem]"
                    );
                    if (!cards.length) {
                        cards = document.querySelectorAll("[class*=card], [class*=Card]");
                    }
                    var maps = Array.from(cards).filter(function(el) {
                        return el.textContent.trim().length > 0 && el.offsetParent !== null;
                    }).slice(0, 30).map(function(el) {
                        var title = el.querySelector("[class*=title], [class*=name], h3, h4, span");
                        var time = el.querySelector("[class*=time], [class*=date], [class*=modify]");
                        return {
                            title: title ? title.textContent.trim().substring(0, 80) : el.textContent.trim().substring(0, 40),
                            time: time ? time.textContent.trim() : ""
                        };
                    });
                    return JSON.stringify({ok: true, count: maps.length, maps: maps});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        result = json.loads(r) if r else {"ok": False}
        machine.transition(XMState.VIEWING_HOME, {"url": cdp.evaluate("window.location.href")})
        return result
    except Exception as e:
        machine.transition(XMState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_sidebar(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read sidebar navigation items."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                try {
                    var body = document.body ? document.body.innerText : '';
                    var sections = ['Recents', 'Starred', 'All Maps', 'Shared', 'Trash'];
                    var found = sections.filter(function(s) { return body.includes(s); });
                    return JSON.stringify({ok: true, sections: found});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_map(title: str = "New Mind Map", port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new mind map using the XMind UI.

    Uses MCP interaction interfaces to click the 'New Map' button and
    set the initial title.
    """
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    interact = _load_interact()

    try:
        machine.transition(XMState.CREATING, {"map_title": title})

        # Navigate to home if not there
        url = cdp.evaluate("window.location.href") or ""
        if "/home" not in str(url) and "/recents" not in str(url):
            cdp.evaluate(f"window.location.href = {json.dumps(XMIND_HOME)}")
            time.sleep(3)

        # Click 'New Map' or '+' button
        new_btn = interact.mcp_wait_and_click(
            cdp,
            'button[class*="new"], button[class*="create"], [class*="new-map"], '
            '[class*="NewMap"], [aria-label*="new"], [aria-label*="New"], '
            'button[class*="primary"]',
            label="Create new map", timeout=8, dwell=1.0,
            color="#f44336",
        )

        if not new_btn.get("ok"):
            machine.transition(XMState.ERROR, {"error": "New map button not found"})
            return {"ok": False, "error": "Could not find 'New Map' button", **machine.to_dict()}

        time.sleep(3)

        # Check if we're now in the map editor
        new_url = cdp.evaluate("window.location.href") or ""
        machine.set_url(str(new_url))

        machine.transition(XMState.VIEWING_MAP, {"map_title": title, "url": str(new_url)})
        return {"ok": True, "action": "created", "url": str(new_url), **machine.to_dict()}

    except Exception as e:
        machine.transition(XMState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e), **machine.to_dict()}


def open_map(map_title: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open an existing mind map by clicking its card on the home page."""
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    interact = _load_interact()

    try:
        machine.transition(XMState.NAVIGATING, {"map_title": map_title})

        # Navigate to home first
        url = cdp.evaluate("window.location.href") or ""
        if "/home" not in str(url) and "/recents" not in str(url):
            cdp.evaluate(f"window.location.href = {json.dumps(XMIND_HOME)}")
            time.sleep(3)

        # Find the map card by title text
        safe_title = map_title.replace("'", "\\'")
        selector = f"""
            [class*="file-card"], [class*="FileCard"], [class*="map-card"],
            [class*="MapCard"], [class*="card-item"], [class*="CardItem"]
        """.strip()

        # Use JS to find the card containing the title text
        found = cdp.evaluate(f"""
            (function() {{
                var cards = document.querySelectorAll('{selector}');
                for (var i = 0; i < cards.length; i++) {{
                    if (cards[i].textContent.includes('{safe_title}')) {{
                        cards[i].setAttribute('data-xmind-target', 'true');
                        return 'found';
                    }}
                }}
                return 'not_found';
            }})()
        """)

        if found == "found":
            result = interact.mcp_click(
                cdp, '[data-xmind-target="true"]',
                label=f"Open: {map_title}", dwell=1.0, color="#f44336",
            )
            time.sleep(3)
            new_url = cdp.evaluate("window.location.href") or ""
            machine.set_url(str(new_url))
            machine.transition(XMState.VIEWING_MAP, {"map_title": map_title, "url": str(new_url)})
            return {"ok": True, "action": "opened", "url": str(new_url), **machine.to_dict()}

        machine.transition(XMState.ERROR, {"error": f"Map not found: {map_title}"})
        return {"ok": False, "error": f"Map '{map_title}' not found", **machine.to_dict()}

    except Exception as e:
        machine.transition(XMState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e), **machine.to_dict()}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current session and state machine status."""
    machine = get_machine(_session_name)
    status = machine.to_dict()
    session = _get_or_create_session(port)
    if session:
        status["session_active"] = True
        status["session_id"] = session.session_id
        status["window_id"] = session.window_id
    else:
        status["session_active"] = False
    return status
