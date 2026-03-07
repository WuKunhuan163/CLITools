"""Figma operations via CDMCP (Chrome DevTools MCP).

Uses CDMCP sessions to manage figma.com tabs with visual overlays,
state machine tracking, and MCP interaction interfaces.
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

from tool.FIGMA.logic.chrome.state_machine import (
    FigmaState, get_machine, FigmaStateMachine,
)

FIGMA_HOME = "https://www.figma.com/files"
_session_name = "figma"

_CDMCP_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent / "GOOGLE.CDMCP"
_OVERLAY_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "session_manager.py"
_INTERACT_PATH = _CDMCP_TOOL_DIR / "logic" / "cdp" / "interact.py"
_TOOL_DIR = Path(__file__).resolve().parent.parent.parent

_fg_session = None


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
    global _fg_session
    if _fg_session is not None:
        cdp = _fg_session.get_cdp()
        if cdp:
            return _fg_session
        _fg_session = None

    sm = _load_session_mgr()
    existing = sm.get_session(_session_name)
    if existing:
        cdp = existing.get_cdp()
        if cdp:
            _fg_session = existing
            return existing
        sm.close_session(_session_name)
    return None


def _reapply_overlays(cdp, session, port):
    overlay = _load_overlay()
    tab_id = session.lifetime_tab_id
    if tab_id:
        overlay.pin_tab_by_target_id(tab_id, pinned=True, port=port)
        overlay.activate_tab(tab_id, port)
    overlay.inject_favicon(cdp, svg_color="#a259ff", letter="F")
    overlay.inject_badge(cdp, text="Figma MCP", color="#a259ff")
    overlay.inject_focus(cdp, color="#a259ff")


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot a Figma CDMCP session using the unified CDMCP boot interface."""
    global _fg_session
    machine = get_machine(_session_name)

    if machine.state not in (FigmaState.UNINITIALIZED, FigmaState.ERROR):
        existing = _get_or_create_session(port)
        if existing:
            return {"ok": True, "action": "already_booted", **machine.to_dict()}

    if machine.state == FigmaState.ERROR:
        machine.transition(FigmaState.RECOVERING)
        if not machine.can_recover():
            machine.reset()
        machine.transition(FigmaState.UNINITIALIZED)

    machine.transition(FigmaState.BOOTING, {"url": FIGMA_HOME})

    sm = _load_session_mgr()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)

    if not boot_result.get("ok"):
        machine.transition(FigmaState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _fg_session = boot_result.get("session")

    # Open Figma in a new tab within the session
    tab_info = _fg_session.require_tab(
        "figma", url_pattern="figma.com",
        open_url=FIGMA_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        overlay = _load_overlay()
        fg_cdp = CDPSession(tab_info["ws"])
        overlay.inject_favicon(fg_cdp, svg_color="#a259ff", letter="F")
        overlay.inject_badge(fg_cdp, text="Figma MCP", color="#a259ff")
        overlay.inject_focus(fg_cdp, color="#a259ff")

    machine.transition(FigmaState.IDLE)
    machine.set_url(FIGMA_HOME)

    return {"ok": True, "action": "booted", **machine.to_dict()}


def _ensure_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    """Get an active CDP session for the Figma tab, booting if needed."""
    global _fg_session
    machine = get_machine(_session_name)

    session = _get_or_create_session(port)
    if not session:
        if machine.state == FigmaState.UNINITIALIZED:
            r = boot_session(port)
            if not r.get("ok"):
                return None
            session = _get_or_create_session(port)
        elif machine.state == FigmaState.ERROR:
            return _recover(port)
        else:
            r = boot_session(port)
            if not r.get("ok"):
                return None
            session = _get_or_create_session(port)

    if not session:
        return None

    tab_info = session.require_tab(
        "figma", url_pattern="figma.com",
        open_url=FIGMA_HOME, auto_open=True, wait_sec=10,
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

    machine.transition(FigmaState.RECOVERING)
    r = boot_session(port)
    if not r.get("ok"):
        return None

    target = machine.get_recovery_target()
    url = target.get("url", FIGMA_HOME)
    session = _get_or_create_session(port)
    if session:
        cdp = session.get_cdp()
        if cdp and url != FIGMA_HOME:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(3)
        return cdp
    return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "authenticated": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var isLogin = url.includes("/login");
                var hasAvatar = !!document.querySelector('[data-testid="avatar"], .avatar, img[alt*="avatar"]');
                return JSON.stringify({
                    ok: true, url: url, title: title,
                    isLogin: isLogin,
                    authenticated: hasAvatar && !isLogin
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                var url = window.location.href;
                var isFile = url.includes('/design/') || url.includes('/file/');
                var isBoard = url.includes('/board/');
                var section = isFile ? 'file' : (isBoard ? 'board' : 'home');
                return JSON.stringify({
                    ok: true, url: url, title: document.title, section: section,
                    isFile: isFile, isBoard: isBoard
                });
            })()
        """)
        result = json.loads(r) if r else {"ok": False}
        machine = get_machine(_session_name)
        url = result.get("url", "")
        machine.set_url(url)
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_files(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        machine.transition(FigmaState.NAVIGATING, {"action": "list_files"})
        r = cdp.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll(
                        '[class*="file_list_tile"], [class*="recent_file"], ' +
                        '[class*="file-card"], [data-testid*="file"]'
                    );
                    if (!items.length) {
                        items = document.querySelectorAll('[class*="tile"], [class*="Tile"]');
                    }
                    var files = [];
                    for (var i = 0; i < Math.min(items.length, 30); i++) {
                        var el = items[i];
                        if (!el.textContent.trim()) continue;
                        var title = el.querySelector('[class*="title"], [class*="name"], span');
                        var time = el.querySelector('[class*="time"], [class*="date"]');
                        files.push({
                            title: title ? title.textContent.trim().substring(0, 80) : el.textContent.trim().substring(0, 40),
                            modified: time ? time.textContent.trim() : ''
                        });
                    }
                    return JSON.stringify({ok: true, count: files.length, files: files});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        result = json.loads(r) if r else {"ok": False}
        machine.transition(FigmaState.VIEWING_HOME, {"url": cdp.evaluate("window.location.href")})
        return result
    except Exception as e:
        machine.transition(FigmaState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def open_file(file_title: str, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}

    interact = _load_interact()

    try:
        machine.transition(FigmaState.NAVIGATING, {"file_name": file_title})

        safe = file_title.replace("'", "\\'")
        found = cdp.evaluate(f"""
            (function() {{
                var items = document.querySelectorAll(
                    '[class*="file_list_tile"], [class*="recent_file"], ' +
                    '[class*="file-card"], [data-testid*="file"], [class*="tile"]'
                );
                for (var i = 0; i < items.length; i++) {{
                    if (items[i].textContent.includes('{safe}')) {{
                        items[i].setAttribute('data-figma-target', 'true');
                        return 'found';
                    }}
                }}
                return 'not_found';
            }})()
        """)

        if found == "found":
            result = interact.mcp_click(
                cdp, '[data-figma-target="true"]',
                label=f"Open: {file_title}", dwell=1.0, color="#a259ff",
            )
            time.sleep(3)
            new_url = cdp.evaluate("window.location.href") or ""
            machine.set_url(str(new_url))
            machine.transition(FigmaState.VIEWING_FILE, {"file_name": file_title, "url": str(new_url)})
            return {"ok": True, "action": "opened", "url": str(new_url), **machine.to_dict()}

        machine.transition(FigmaState.ERROR, {"error": f"File not found: {file_title}"})
        return {"ok": False, "error": f"File '{file_title}' not found", **machine.to_dict()}

    except Exception as e:
        machine.transition(FigmaState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e), **machine.to_dict()}


def take_screenshot(output_path: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
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


def navigate_home(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        machine.transition(FigmaState.NAVIGATING, {"action": "go_home"})
        cdp.evaluate(f"window.location.href = {json.dumps(FIGMA_HOME)}")
        time.sleep(3)
        url = cdp.evaluate("window.location.href") or ""
        machine.set_url(str(url))
        machine.transition(FigmaState.VIEWING_HOME, {"url": str(url)})
        return {"ok": True, "url": str(url)}
    except Exception as e:
        machine.transition(FigmaState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def get_layers(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get layers/frames from the current Figma file."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        r = cdp.evaluate("""
            (function() {
                try {
                    var layers = document.querySelectorAll(
                        '[class*="layer_name"], [class*="LayerName"], ' +
                        '[class*="layer-name"], [class*="object_row"]'
                    );
                    var items = [];
                    for (var i = 0; i < Math.min(layers.length, 50); i++) {
                        var el = layers[i];
                        var text = el.textContent ? el.textContent.trim() : '';
                        if (text) items.push({name: text.substring(0, 80), index: i});
                    }
                    return JSON.stringify({ok: true, count: items.length, layers: items});
                } catch(e) {
                    return JSON.stringify({ok: false, error: e.toString()});
                }
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
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
