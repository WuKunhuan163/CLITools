"""XMind operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP sessions for auth state detection and session management only.
UI automation functions (create/open/edit maps, node operations, export)
are disabled due to XMind ToS violations.

XMind membership agreement (July 2025) explicitly prohibits "using plugins,
external tools, or unauthorized third-party tools." Use the XMind SDK
(npm: xmind) for programmatic file manipulation instead.
"""

import json
import time
import importlib.util
from pathlib import Path
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
)

from tool.XMIND.logic.chrome.state_machine import (
    XMState, get_machine,
)

XMIND_HOME = "https://app.xmind.com"
_session_name = "xmind"

# TODO: Migrate to XMind SDK (npm: xmind) for file operations.
# UI automation violates XMind ToS. See for_agent.md ## ToS Compliance.
_TOS_ERR = "Disabled: XMind ToS prohibits external tools and UI automation. Use XMind SDK instead."

_CDMCP_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "GOOGLE.CDMCP"
_OVERLAY_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_INTERACT_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "interact.py"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent

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
    """Boot an XMind CDMCP session using the unified CDMCP boot interface."""
    global _xm_session
    machine = get_machine(_session_name)

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

    sm = _load_session_mgr()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)

    if not boot_result.get("ok"):
        machine.transition(XMState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _xm_session = boot_result.get("session")

    tab_info = _xm_session.require_tab(
        "xmind", url_pattern="xmind.com",
        open_url=XMIND_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        overlay = _load_overlay()
        xm_cdp = CDPSession(tab_info["ws"])
        overlay.inject_favicon(xm_cdp, svg_color="#f44336", letter="X")
        overlay.inject_badge(xm_cdp, text="XMind MCP", color="#f44336")
        overlay.inject_focus(xm_cdp, color="#f44336")

    machine.transition(XMState.IDLE)
    machine.set_url(XMIND_HOME)

    return {"ok": True, "action": "booted", **machine.to_dict()}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get an active CDP session for the XMind tab, booting if needed."""
    global _xm_session
    machine = get_machine(_session_name)

    session = _get_or_create_session(port)
    if not session:
        if machine.state == XMState.UNINITIALIZED:
            r = boot_session(port)
            if not r.get("ok"):
                return None
            session = _get_or_create_session(port)
        elif machine.state == XMState.ERROR:
            return _recover(port)
        else:
            r = boot_session(port)
            if not r.get("ok"):
                return None
            session = _get_or_create_session(port)

    if not session:
        return None

    tab_info = session.require_tab(
        "xmind", url_pattern="xmind.com",
        open_url=XMIND_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        cdp = CDPSession(tab_info["ws"])
        try:
            has_badge = cdp.evaluate(f"!!document.getElementById('{_load_overlay().CDMCP_BADGE_ID}')")
            if not has_badge:
                _reapply_overlays(cdp, session, port)
        except Exception:
            pass
        return cdp

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


# ----- Public API (safe: read-only / auth / session) -----

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


def take_screenshot(output_path: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Take a screenshot of the XMind page (passive, non-invasive)."""
    from logic.chrome.session import capture_screenshot
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    try:
        img = capture_screenshot(cdp)
        if not img:
            return {"ok": False, "error": "Screenshot capture failed"}

        if not output_path:
            report_dir = _TOOL_DIR / "data" / "report"
            report_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(report_dir / "screenshot.png")

        with open(output_path, "wb") as f:
            f.write(img)
        return {"ok": True, "path": output_path, "size": len(img)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current session and state machine status."""
    machine = get_machine(_session_name)
    status = machine.to_dict()
    status["ok"] = True
    session = _get_or_create_session(port)
    if session:
        status["session_active"] = True
        status["session_id"] = session.session_id
        status["window_id"] = session.window_id
    else:
        status["session_active"] = False
    return status


def get_mcp_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Collect MCP state: URL, title, session status (node scraping disabled)."""
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
                    is_editor: !window.location.href.includes('/home') &&
                               !window.location.href.includes('/recents'),
                    note: "Node scraping disabled due to ToS. Use XMind SDK for file operations."
                });
            })()
        """)
        result = json.loads(r) if r else {"ok": False}
        machine = get_machine(_session_name)
        result["state_machine"] = machine.to_dict()
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# DISABLED: UI automation functions (ToS violation)
# TODO: Migrate to XMind SDK (npm: xmind) for programmatic file operations.
# ---------------------------------------------------------------------------

def get_maps(port: int = CDP_PORT) -> Dict[str, Any]:
    """List mind maps. DISABLED: violates XMind ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def get_sidebar(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read sidebar. DISABLED: violates XMind ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def create_map(title: str = "New Mind Map", port: int = CDP_PORT) -> Dict[str, Any]:
    """Create map. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def open_map(map_title: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open map. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def add_node(parent_text: Optional[str] = None, text: str = "New Topic",
             as_child: bool = True, port: int = CDP_PORT) -> Dict[str, Any]:
    """Add node. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def edit_node(node_text: str, new_text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Edit node. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def delete_node(node_text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete node. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def navigate_home(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate home. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def get_map_nodes(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get nodes. DISABLED: violates XMind ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def undo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Undo. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def redo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Redo. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def zoom(level: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Zoom. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def export_map(fmt: str = "png", port: int = CDP_PORT) -> Dict[str, Any]:
    """Export map. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def insert_item(item_type: str, text: Optional[str] = None,
                node: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Insert item. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def rename_map(new_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Rename map. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def fit_map(port: int = CDP_PORT) -> Dict[str, Any]:
    """Fit map. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def select_all(port: int = CDP_PORT) -> Dict[str, Any]:
    """Select all. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def copy_node(node_text: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Copy node. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def paste_node(port: int = CDP_PORT) -> Dict[str, Any]:
    """Paste node. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def collapse_node(node_text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Collapse branch. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def expand_node(node_text: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Expand branch. DISABLED: violates XMind ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}
