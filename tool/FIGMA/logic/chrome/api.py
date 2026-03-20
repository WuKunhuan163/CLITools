"""ToS-restricted: FIGMA DOM automation disabled.

Use official API: https://www.figma.com/developers/api
Only auth/session functions remain active.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    capture_screenshot,
)

from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_interact,
)

from tool.FIGMA.logic.chrome.state_machine import (
    FigmaState, get_machine,
)

FIGMA_HOME = "https://www.figma.com/files"
_session_name = "figma"
_TOOL_DIR = Path(__file__).resolve().parent.parent.parent

_fg_session = None


_TOS_ERR = ("Disabled: Figma ToS prohibits scraping/automation. Use Figma REST API (api.figma.com) instead.")

_AUTH_FUNCS = frozenset({
    "boot_session", "get_session_status", "get_auth_state",
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


def _load_overlay():
    return load_cdmcp_overlay()


def _load_session_mgr():
    return load_cdmcp_sessions()


def _load_interact():
    return load_cdmcp_interact()


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
                var hasProfile = !!document.querySelector('[data-testid="ProfileButton"]');
                var hasAccount = !!document.querySelector('[aria-label="Open account dropdown"]');
                var hasFuid = url.includes("fuid=");
                return JSON.stringify({
                    ok: true, url: url, title: title,
                    isLogin: isLogin,
                    authenticated: (hasProfile || hasAccount || hasFuid) && !isLogin
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
                    var items = document.querySelectorAll('[data-index]');
                    if (!items.length) {
                        items = document.querySelectorAll(
                            '[class*="tiles_view"], [class*="file_tile"], [class*="recent_file"]'
                        );
                    }
                    var files = [];
                    for (var i = 0; i < Math.min(items.length, 30); i++) {
                        var el = items[i];
                        var text = (el.textContent || '').trim();
                        if (!text) continue;
                        var parts = text.split('Edited');
                        var title = parts[0].trim();
                        var modified = parts.length > 1 ? 'Edited' + parts[1].trim().split('\\n')[0] : '';
                        var idx = el.getAttribute('data-index') || String(i);
                        files.push({
                            title: title.substring(0, 80),
                            modified: modified.substring(0, 40),
                            index: idx,
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

        safe_title = json.dumps(file_title)
        found = cdp.evaluate(f"""
            (function() {{
                var title = {safe_title};
                var items = document.querySelectorAll('[data-index]');
                for (var i = 0; i < items.length; i++) {{
                    if (items[i].textContent.includes(title)) {{
                        items[i].setAttribute('data-figma-target', 'true');
                        return 'found';
                    }}
                }}
                return 'not_found';
            }})()
        """)

        if found == "found":
            interact.mcp_click(
                cdp, '[data-figma-target="true"]',
                label=f"Open: {file_title}", dwell=0.5, color="#a259ff",
                tool_name="Figma",
            )
            time.sleep(0.5)
            interact.mcp_click(
                cdp, '[data-figma-target="true"]',
                label=f"Open: {file_title}", dwell=0.3, color="#a259ff",
                tool_name="Figma",
            )
            time.sleep(5)
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


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------

def create_file(file_type: str = "design", port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new Figma file (design, figjam, or slides)."""
    machine = get_machine(_session_name)
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _load_interact()
    try:
        btn_map = {
            "design": "new-design-file-button",
            "figjam": "new-whiteboard-file-button",
            "slides": "new-slides-file-button",
        }
        testid = btn_map.get(file_type.lower(), btn_map["design"])
        selector = f'[data-testid="{testid}"]'
        result = interact.mcp_click(cdp, selector,
                                    label=f"New {file_type}", dwell=0.5,
                                    color="#a259ff", tool_name="Figma")
        if not result.get("ok"):
            return result
        time.sleep(5)
        new_url = cdp.evaluate("window.location.href") or ""
        machine.set_url(str(new_url))
        machine.transition(FigmaState.VIEWING_FILE, {"url": str(new_url)})
        return {"ok": True, "action": "created", "type": file_type,
                "url": str(new_url), **machine.to_dict()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Canvas interaction (when inside a design file)
# ---------------------------------------------------------------------------

def zoom(level: str = "fit", port: int = CDP_PORT) -> Dict[str, Any]:
    """Zoom the canvas. level: 'in', 'out', 'fit', '50', '100', '200'."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        if level == "in":
            _send_key(cdp, "+", modifiers=mod)
        elif level == "out":
            _send_key(cdp, "-", modifiers=mod)
        elif level == "fit":
            _send_key(cdp, "1", modifiers=mod + 1)
        else:
            pct = int(level)
            cdp.evaluate(f"""
                (function() {{
                    if (typeof figma !== 'undefined' && figma.viewport) {{
                        figma.viewport.zoom = {pct / 100};
                    }}
                }})()
            """)
        return {"ok": True, "action": "zoom", "level": level}
    except Exception as e:
        return {"ok": False, "error": str(e)}


_KEY_CODES = {
    "v": 86, "f": 70, "r": 82, "o": 79, "l": 76,
    "p": 80, "t": 84, "h": 72, "a": 65, "z": 90,
    "e": 69, "s": 83, "c": 67, "x": 88, "g": 71,
}


_SPECIAL_KEYS = {
    "Escape": (27, "Escape"), "Enter": (13, "Enter"),
    "Backspace": (8, "Backspace"), "Tab": (9, "Tab"),
    "Delete": (46, "Delete"), "ArrowUp": (38, "ArrowUp"),
    "ArrowDown": (40, "ArrowDown"), "ArrowLeft": (37, "ArrowLeft"),
    "ArrowRight": (39, "ArrowRight"), "+": (187, "Equal"),
    "-": (189, "Minus"), "1": (49, "Digit1"),
}


def _send_key(cdp, key: str, modifiers: int = 0):
    """Send a key press to Figma using the correct rawKeyDown+char+keyUp sequence.

    Uses fire-and-forget (send_only) to avoid blocking on Figma's
    event flood when the WebGL canvas processes input.
    """
    is_special = key in _SPECIAL_KEYS
    if is_special:
        vk, code = _SPECIAL_KEYS[key]
    elif len(key) == 1 and key.isalpha():
        code = f"Key{key.upper()}"
        vk = _KEY_CODES.get(key.lower(), ord(key.upper()))
    else:
        code = key
        vk = _KEY_CODES.get(key.lower(), ord(key.upper()) if len(key) == 1 else 0)

    cdp.send_only("Input.dispatchKeyEvent", {
        "type": "rawKeyDown", "key": key, "code": code,
        "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
        "modifiers": modifiers})
    if not modifiers and not is_special:
        cdp.send_only("Input.dispatchKeyEvent", {
            "type": "char", "key": key, "code": code,
            "text": key, "unmodifiedText": key})
    cdp.send_only("Input.dispatchKeyEvent", {
        "type": "keyUp", "key": key, "code": code,
        "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk,
        "modifiers": modifiers})


def _mouse_drag(cdp, x1: int, y1: int, x2: int, y2: int, steps: int = 10):
    """Perform a smooth mouse drag from (x1,y1) to (x2,y2) via raw CDP events.

    Uses fire-and-forget (send_only) to avoid blocking on Figma's WebGL
    event flood. Drains the websocket buffer afterward.
    """
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": x1, "y": y1})
    time.sleep(0.05)
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x1, "y": y1,
        "button": "left", "clickCount": 1, "buttons": 1})
    time.sleep(0.05)
    for i in range(1, steps + 1):
        frac = i / steps
        mx = int(x1 + (x2 - x1) * frac)
        my = int(y1 + (y2 - y1) * frac)
        cdp.send_only("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": mx, "y": my,
            "button": "left", "buttons": 1})
        time.sleep(0.02)
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x2, "y": y2,
        "button": "left", "clickCount": 1, "buttons": 0})
    time.sleep(0.3)
    cdp.drain()


def _figma_drag(cdp, x1: int, y1: int, x2: int, y2: int, steps: int = 10):
    """Figma-specific drag that auto-locks, enables passthrough, and counts MPC.

    Unlike interact.mcp_drag, this avoids JS evaluation during mouse events
    to prevent blocking on Figma's WebGL canvas.
    """
    interact = _load_interact()
    ov = _load_overlay()
    interact._ensure_locked(cdp, "Figma")
    ov.set_lock_passthrough(cdp, True)
    try:
        _mouse_drag(cdp, x1, y1, x2, y2, steps=steps)
    finally:
        ov.set_lock_passthrough(cdp, False)
    interact._count_mcp_op(cdp)


def _mouse_click(cdp, x: int, y: int, double: bool = False):
    """Click at the given viewport coordinates."""
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mouseMoved", "x": x, "y": y})
    time.sleep(0.05)
    count = 2 if double else 1
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mousePressed", "x": x, "y": y,
        "button": "left", "clickCount": count, "buttons": 1})
    time.sleep(0.05)
    cdp.send_only("Input.dispatchMouseEvent", {
        "type": "mouseReleased", "x": x, "y": y,
        "button": "left", "clickCount": count, "buttons": 0})
    cdp.drain()


def _canvas_center(cdp) -> tuple:
    """Return viewport center of the canvas element."""
    r = cdp.evaluate("""
        (function() {
            var c = document.querySelector("canvas");
            if (!c) return null;
            var r = c.getBoundingClientRect();
            return JSON.stringify({x: Math.round(r.left + r.width/2),
                                   y: Math.round(r.top + r.height/2)});
        })()
    """)
    if r:
        d = json.loads(r)
        return d["x"], d["y"]
    return 500, 300


def select_tool(tool_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Select a Figma tool by keyboard shortcut.

    Supported: move (v), frame (f), rectangle (r), ellipse (o),
    line (l), pen (p), text (t), hand (h).
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    shortcuts = {
        "move": "v", "frame": "f", "rectangle": "r", "ellipse": "o",
        "line": "l", "pen": "p", "text": "t", "hand": "h",
    }
    key = shortcuts.get(tool_name.lower())
    if not key:
        return {"ok": False, "error": f"Unknown tool: {tool_name}. "
                f"Available: {', '.join(shortcuts.keys())}"}
    try:
        _send_key(cdp, key)
        return {"ok": True, "tool": tool_name, "shortcut": key}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_rectangle(x: int, y: int, width: int = 100, height: int = 100,
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Draw a rectangle at the specified canvas viewport position."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "r")
        time.sleep(0.3)
        _figma_drag(cdp, x, y, x + width, y + height)
        time.sleep(0.3)
        _send_key(cdp, "v")
        return {"ok": True, "action": "draw_rectangle",
                "x": x, "y": y, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_text(text: str, x: int = 400, y: int = 300,
             port: int = CDP_PORT) -> Dict[str, Any]:
    """Add text to the canvas at the specified position."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _load_interact()
    ov = _load_overlay()
    try:
        interact._ensure_locked(cdp, "Figma")

        ov.set_lock_passthrough(cdp, True)
        try:
            cx, cy = _canvas_center(cdp)
            _mouse_click(cdp, cx, cy)
            time.sleep(0.15)
            _send_key(cdp, "Escape")
            time.sleep(0.15)
            _send_key(cdp, "v")
            time.sleep(0.15)
            _mouse_click(cdp, cx, cy)
            time.sleep(0.15)

            _send_key(cdp, "t")
            time.sleep(0.4)
            _mouse_click(cdp, x, y)
            time.sleep(0.6)

            from interface.chrome import insert_text
            for char in text:
                insert_text(cdp, char)
                time.sleep(0.03)
            time.sleep(0.3)
            _send_key(cdp, "Escape")
            time.sleep(0.2)
            _send_key(cdp, "v")
        finally:
            ov.set_lock_passthrough(cdp, False)

        interact._count_mcp_op(cdp)
        return {"ok": True, "action": "add_text", "text": text, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def undo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Undo the last action."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "z", modifiers=mod)
        return {"ok": True, "action": "undo"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def redo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Redo the last undone action."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "z", modifiers=mod + 1)
        return {"ok": True, "action": "redo"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def rename_file(new_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Rename the current file by clicking the title and typing."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _load_interact()
    try:
        r = interact.mcp_click(cdp, '[class*="filename"], [data-testid="filename"]',
                               label="File name", dwell=0.3, color="#a259ff",
                               tool_name="Figma")
        if not r.get("ok"):
            r = interact.mcp_click(cdp, '.filename--singleLine--FJRMi',
                                   label="File name", dwell=0.3, color="#a259ff",
                                   tool_name="Figma")
        time.sleep(0.5)
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "a", modifiers=mod)
        time.sleep(0.2)
        from interface.chrome import insert_text
        for char in new_name:
            insert_text(cdp, char)
            time.sleep(0.03)
        _send_key(cdp, "Enter")
        time.sleep(0.3)
        ov = _load_overlay()
        ov.set_lock_passthrough(cdp, True)
        try:
            cx, cy = _canvas_center(cdp)
            _mouse_click(cdp, cx, cy)
        finally:
            ov.set_lock_passthrough(cdp, False)
        return {"ok": True, "action": "renamed", "name": new_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def export(format: str = "png", port: int = CDP_PORT) -> Dict[str, Any]:
    """Export the current selection or page. format: png, svg, jpg, pdf."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "e", modifiers=mod + 1)
        time.sleep(2)
        return {"ok": True, "action": "export_dialog_opened", "format": format}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_ellipse(x: int, y: int, width: int = 100, height: int = 100,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Draw an ellipse at the specified canvas viewport position."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "o")
        time.sleep(0.3)
        _figma_drag(cdp, x, y, x + width, y + height)
        time.sleep(0.3)
        _send_key(cdp, "v")
        return {"ok": True, "action": "draw_ellipse",
                "x": x, "y": y, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_line(x1: int, y1: int, x2: int, y2: int,
              port: int = CDP_PORT) -> Dict[str, Any]:
    """Draw a line from (x1,y1) to (x2,y2)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "l")
        time.sleep(0.3)
        _figma_drag(cdp, x1, y1, x2, y2)
        time.sleep(0.2)
        _send_key(cdp, "Escape")
        time.sleep(0.1)
        _send_key(cdp, "v")
        return {"ok": True, "action": "draw_line",
                "x1": x1, "y1": y1, "x2": x2, "y2": y2}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_frame(x: int, y: int, width: int = 200, height: int = 200,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """Draw a frame at the specified canvas viewport position."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "f")
        time.sleep(0.3)
        _figma_drag(cdp, x, y, x + width, y + height)
        time.sleep(0.3)
        _send_key(cdp, "v")
        return {"ok": True, "action": "draw_frame",
                "x": x, "y": y, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def select_all(port: int = CDP_PORT) -> Dict[str, Any]:
    """Select all objects on the canvas (Cmd/Ctrl+A)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "a", modifiers=mod)
        return {"ok": True, "action": "select_all"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def copy_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Copy the current selection (Cmd/Ctrl+C)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "c", modifiers=mod)
        return {"ok": True, "action": "copy"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def paste_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Paste from clipboard (Cmd/Ctrl+V)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "v", modifiers=mod)
        time.sleep(0.5)
        return {"ok": True, "action": "paste"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def duplicate_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Duplicate the current selection (Cmd/Ctrl+D)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "d", modifiers=mod)
        time.sleep(0.3)
        return {"ok": True, "action": "duplicate"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete the current selection."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "Backspace")
        return {"ok": True, "action": "delete"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def group_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Group selected objects (Cmd/Ctrl+G)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "g", modifiers=mod)
        return {"ok": True, "action": "group"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ungroup_selection(port: int = CDP_PORT) -> Dict[str, Any]:
    """Ungroup selected objects (Cmd/Ctrl+Shift+G)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "g", modifiers=mod + 1)
        return {"ok": True, "action": "ungroup"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def change_fill_color(hex_color: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Change the fill color of the selected element.

    Args:
        hex_color: 6-digit hex color without # (e.g. 'FF5733').
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        hex_color = hex_color.lstrip("#").upper()
        r = cdp.evaluate(f"""
            (function() {{
                var input = document.querySelector(
                    '[class*="color_picker"] input, ' +
                    '[class*="hexInput"] input, ' +
                    'input[aria-label*="color" i], ' +
                    'input[aria-label*="hex" i]'
                );
                if (!input) {{
                    var fills = document.querySelectorAll('[class*="fill"] input, [class*="Fill"] input');
                    for (var i = 0; i < fills.length; i++) {{
                        if (fills[i].type === 'text' && fills[i].value.length <= 8) {{
                            input = fills[i];
                            break;
                        }}
                    }}
                }}
                if (!input) return JSON.stringify({{ok: false, error: "No color input found"}});
                input.focus();
                input.value = '{hex_color}';
                input.dispatchEvent(new Event('input', {{bubbles: true}}));
                input.dispatchEvent(new Event('change', {{bubbles: true}}));
                input.dispatchEvent(new KeyboardEvent('keydown', {{key: 'Enter', code: 'Enter', bubbles: true}}));
                return JSON.stringify({{ok: true, color: '{hex_color}'}});
            }})()
        """)
        result = json.loads(r) if r else {"ok": False, "error": "No response"}
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def move_selection(dx: int = 0, dy: int = 0,
                   port: int = CDP_PORT) -> Dict[str, Any]:
    """Move the selected object by (dx, dy) pixels using arrow keys.

    Each arrow key press moves by 1px (or 10px with Shift).
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        for axis, delta, pos_key, neg_key in [
            ("x", dx, "ArrowRight", "ArrowLeft"),
            ("y", dy, "ArrowDown", "ArrowUp"),
        ]:
            if delta == 0:
                continue
            key = pos_key if delta > 0 else neg_key
            abs_d = abs(delta)
            big_steps = abs_d // 10
            small_steps = abs_d % 10
            for _ in range(big_steps):
                _send_key(cdp, key, modifiers=1)
                time.sleep(0.02)
            for _ in range(small_steps):
                _send_key(cdp, key)
                time.sleep(0.02)
        return {"ok": True, "action": "move", "dx": dx, "dy": dy}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def click_canvas(x: int, y: int, double: bool = False,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Click at a specific viewport position on the canvas."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _mouse_click(cdp, x, y, double=double)
        return {"ok": True, "action": "click", "x": x, "y": y, "double": double}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def deselect(port: int = CDP_PORT) -> Dict[str, Any]:
    """Deselect all objects by pressing Escape."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "Escape")
        return {"ok": True, "action": "deselect"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def resize_selection(width: int, height: int,
                     port: int = CDP_PORT) -> Dict[str, Any]:
    """Resize the selected element to exact width/height via the property panel."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    _load_interact()
    try:
        js = f"""
        (function() {{
            var wInputs = document.querySelectorAll('input[aria-label*="idth"], input[placeholder*="W"]');
            var hInputs = document.querySelectorAll('input[aria-label*="eight"], input[placeholder*="H"]');
            var wInput = null, hInput = null;
            wInputs.forEach(function(el) {{ if (!wInput && el.offsetParent) wInput = el; }});
            hInputs.forEach(function(el) {{ if (!hInput && el.offsetParent) hInput = el; }});
            if (wInput && hInput) {{
                var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSet.call(wInput, '{width}');
                wInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                wInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                nativeSet.call(hInput, '{height}');
                hInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                hInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 'resized';
            }}
            return 'inputs_not_found';
        }})()
        """
        result = cdp.evaluate(js)
        if result == "resized":
            _send_key(cdp, "Enter")
            return {"ok": True, "action": "resize", "width": width, "height": height}
        return {"ok": False, "error": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def rotate_selection(degrees: float, port: int = CDP_PORT) -> Dict[str, Any]:
    """Rotate the selected element by setting the rotation value."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        js = f"""
        (function() {{
            var inputs = document.querySelectorAll('input[aria-label*="otation"], input[aria-label*="ngle"]');
            var rotInput = null;
            inputs.forEach(function(el) {{ if (!rotInput && el.offsetParent) rotInput = el; }});
            if (rotInput) {{
                var nativeSet = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSet.call(rotInput, '{degrees}');
                rotInput.dispatchEvent(new Event('input', {{bubbles: true}}));
                rotInput.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 'rotated';
            }}
            return 'input_not_found';
        }})()
        """
        result = cdp.evaluate(js)
        if result == "rotated":
            _send_key(cdp, "Enter")
            return {"ok": True, "action": "rotate", "degrees": degrees}
        return {"ok": False, "error": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_stroke(color: str = "#000000", width: int = 2,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """Add or modify stroke on the selected element."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    interact = _load_interact()
    try:
        interact.mcp_click(cdp, '[class*="stroke"] [class*="add"], '
                               'button[aria-label*="troke"]',
                               label="Add stroke", dwell=0.3, tool_name="Figma")
        time.sleep(0.5)
        hex_val = color.lstrip("#")
        js = f"""
        (function() {{
            var inputs = document.querySelectorAll('input');
            for (var i = 0; i < inputs.length; i++) {{
                var v = inputs[i].value;
                if (v && /^[0-9A-Fa-f]{{6}}$/.test(v)) {{
                    var nativeSet = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeSet.call(inputs[i], '{hex_val}');
                    inputs[i].dispatchEvent(new Event('input', {{bubbles: true}}));
                    inputs[i].dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'color_set';
                }}
            }}
            return 'color_input_not_found';
        }})()
        """
        cdp.evaluate(js)
        _send_key(cdp, "Enter")
        return {"ok": True, "action": "add_stroke", "color": color, "width": width}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def rename_layer(old_name: str, new_name: str,
                 port: int = CDP_PORT) -> Dict[str, Any]:
    """Rename a layer by double-clicking it in the layers panel."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    _load_interact()
    ov = _load_overlay()
    try:
        js = f"""
        (function() {{
            var layers = document.querySelectorAll('[class*="layer_name"], [class*="object_row"]');
            for (var i = 0; i < layers.length; i++) {{
                if (layers[i].textContent.trim() === {json.dumps(old_name)}) {{
                    var rect = layers[i].getBoundingClientRect();
                    return JSON.stringify({{x: rect.x + rect.width/2, y: rect.y + rect.height/2}});
                }}
            }}
            return null;
        }})()
        """
        result = cdp.evaluate(js)
        if not result:
            return {"ok": False, "error": f"Layer '{old_name}' not found"}

        data = json.loads(result)
        x, y = int(data["x"]), int(data["y"])

        ov.set_lock_passthrough(cdp, True)
        try:
            _mouse_click(cdp, x, y, double=True)
            time.sleep(0.5)
            import platform
            mod = 4 if platform.system() == "Darwin" else 2
            _send_key(cdp, "a", modifiers=mod)
            time.sleep(0.1)
            from interface.chrome import insert_text
            for char in new_name:
                insert_text(cdp, char)
                time.sleep(0.02)
            _send_key(cdp, "Enter")
        finally:
            ov.set_lock_passthrough(cdp, False)

        return {"ok": True, "action": "rename_layer",
                "old_name": old_name, "new_name": new_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def switch_mode(mode: str = "design",
                port: int = CDP_PORT) -> Dict[str, Any]:
    """Switch right-panel tab: 'design' or 'prototype'.

    Figma's right panel uses 'Design' and 'Prototype' tabs.
    """
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        tab_names = {
            "design": "Design",
            "prototype": "Prototype",
            "properties": "Design",
            "comments": "Design",
        }
        target = tab_names.get(mode.lower())
        if not target:
            return {"ok": False, "error": f"Unknown mode: {mode}. Use: design, prototype"}

        js = f"""
        (function() {{
            var els = document.querySelectorAll('*');
            for (var i = 0; i < els.length; i++) {{
                if (els[i].textContent.trim() === {json.dumps(target)} && els[i].childElementCount === 0) {{
                    var r = els[i].getBoundingClientRect();
                    if (r.x > 700 && r.y < 80 && r.width < 120) {{
                        return JSON.stringify({{x: r.x + r.width/2, y: r.y + r.height/2}});
                    }}
                }}
            }}
            return null;
        }})()
        """
        result = cdp.evaluate(js)
        if result:
            data = json.loads(result)
            _mouse_click(cdp, int(data["x"]), int(data["y"]))
            return {"ok": True, "action": "switch_mode", "mode": mode}
        return {"ok": False, "error": f"Tab '{target}' not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def close_file(port: int = CDP_PORT) -> Dict[str, Any]:
    """Close current file and return to home page."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        cdp.evaluate("window.location.href = 'https://www.figma.com/files/recents'")
        time.sleep(3)
        return {"ok": True, "action": "close_file"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_editor_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Identify and describe the core editor areas."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        info = cdp.evaluate("""
        (function() {
            var result = {};
            var toolbar = document.querySelector('[class*="toolbar"], [class*="tool_bar"]');
            result.toolbar = toolbar ? {x: toolbar.getBoundingClientRect().x,
                y: toolbar.getBoundingClientRect().y, visible: true} : {visible: false};
            var layers = document.querySelector('[class*="layers_panel"], [class*="left_panel"]');
            result.layers_panel = layers ? {visible: true} : {visible: false};
            var props = document.querySelector('[class*="properties_panel"], [class*="right_panel"]');
            result.properties_panel = props ? {visible: true} : {visible: false};
            var canvas = document.querySelector('canvas');
            result.canvas = canvas ? {width: canvas.width, height: canvas.height, visible: true} : {visible: false};
            result.title = document.title;
            result.url = window.location.href;
            return JSON.stringify(result);
        })()
        """)
        return {"ok": True, "action": "get_editor_info",
                "info": json.loads(info) if info else {}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Advanced: Component operations
# ---------------------------------------------------------------------------

def create_component(port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a component from the current selection (Cmd+Alt+K)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "k", modifiers=mod + 1)
        time.sleep(0.5)
        return {"ok": True, "action": "create_component"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def detach_instance(port: int = CDP_PORT) -> Dict[str, Any]:
    """Detach selected component instance (Cmd+Alt+B)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "b", modifiers=mod + 1)
        time.sleep(0.3)
        return {"ok": True, "action": "detach_instance"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def auto_layout(port: int = CDP_PORT) -> Dict[str, Any]:
    """Add auto layout to selection (Shift+A)."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "a", modifiers=1)
        time.sleep(0.5)
        return {"ok": True, "action": "auto_layout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_comment(text: str, x: int, y: int,
                port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a comment at specified canvas position."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "c")
        time.sleep(0.3)
        _mouse_click(cdp, x, y)
        time.sleep(0.8)
        from interface.chrome import insert_text
        for ch in text:
            insert_text(cdp, ch)
            time.sleep(0.02)
        time.sleep(0.2)
        import platform
        mod = 4 if platform.system() == "Darwin" else 2
        _send_key(cdp, "Enter", modifiers=mod)
        time.sleep(0.5)
        _send_key(cdp, "Escape")
        return {"ok": True, "action": "add_comment", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def create_frame_with_content(name: str, x: int, y: int,
                              width: int, height: int,
                              content_text: str = "",
                              port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a frame and optionally add text content inside it."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        _send_key(cdp, "f")
        time.sleep(0.3)
        _figma_drag(cdp, x, y, x + width, y + height)
        time.sleep(0.5)

        if content_text:
            _send_key(cdp, "t")
            time.sleep(0.3)
            _mouse_click(cdp, x + width // 2, y + height // 2)
            time.sleep(0.5)
            from interface.chrome import insert_text
            for ch in content_text:
                insert_text(cdp, ch)
                time.sleep(0.02)
            _send_key(cdp, "Escape")

        time.sleep(0.3)
        _send_key(cdp, "v")
        return {"ok": True, "action": "create_frame",
                "name": name, "x": x, "y": y, "width": width, "height": height}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_corner_radius(radius: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set corner radius on the selected element via property panel."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        result = cdp.evaluate(f"""
        (function() {{
            var inputs = document.querySelectorAll('input');
            for (var i = 0; i < inputs.length; i++) {{
                var label = inputs[i].getAttribute('aria-label') || '';
                if (label.toLowerCase().includes('corner') || label.toLowerCase().includes('radius')) {{
                    var nativeSet = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeSet.call(inputs[i], '{radius}');
                    inputs[i].dispatchEvent(new Event('input', {{bubbles: true}}));
                    inputs[i].dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'set';
                }}
            }}
            return 'not_found';
        }})()
        """)
        if result == "set":
            _send_key(cdp, "Enter")
            return {"ok": True, "action": "set_corner_radius", "radius": radius}
        return {"ok": False, "error": "Corner radius input not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_plugins_menu(port: int = CDP_PORT) -> Dict[str, Any]:
    """Open the Figma main menu and navigate to Plugins submenu."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        cdp.evaluate("document.querySelector('canvas').focus()")
        time.sleep(0.3)

        btn = cdp.evaluate("""
        (function() {
            var svg = document.querySelector('svg[data-fpl-icon-size]');
            var btn = svg ? svg.closest('button') : null;
            if (btn) { btn.click(); return 'ok'; }
            return null;
        })()
        """)
        if not btn:
            return {"ok": False, "error": "Main menu button not found"}
        time.sleep(1)

        cdp.evaluate("""
        (function() {
            var els = document.querySelectorAll('*');
            for (var i = 0; i < els.length; i++) {
                if (els[i].textContent.trim() === 'Plugins' && els[i].childElementCount <= 1) {
                    var r = els[i].getBoundingClientRect();
                    if (r.x < 200 && r.y > 50) { els[i].click(); return 'ok'; }
                }
            }
            return null;
        })()
        """)
        time.sleep(0.5)

        submenu = cdp.evaluate("""
        (function() {
            var result = [];
            var all = document.querySelectorAll('*');
            for (var i = 0; i < all.length; i++) {
                var r = all[i].getBoundingClientRect();
                if (r.x > 140 && r.x < 400 && r.y > 200 && r.height > 10 && r.height < 40 && r.width > 30) {
                    var t = all[i].textContent.trim();
                    if (t && t.length < 50 && all[i].childElementCount <= 1) result.push(t);
                }
            }
            return JSON.stringify([...new Set(result)]);
        })()
        """)
        _send_key(cdp, "Escape"); time.sleep(0.2)
        _send_key(cdp, "Escape"); time.sleep(0.2)
        items = json.loads(submenu) if submenu else []
        return {"ok": True, "action": "open_plugins_menu", "items": items}
    except Exception as e:
        _send_key(cdp, "Escape")
        return {"ok": False, "error": str(e)}


def switch_panel_tab(tab: str = "design", port: int = CDP_PORT) -> Dict[str, Any]:
    """Switch between Design and Prototype tabs in the right panel."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        target = tab.capitalize()
        if target not in ("Design", "Prototype"):
            return {"ok": False, "error": f"Unknown tab: {tab}. Use 'design' or 'prototype'."}
        result = cdp.evaluate(f"""
        (function() {{
            var els = document.querySelectorAll('*');
            for (var i = 0; i < els.length; i++) {{
                if (els[i].textContent.trim() === '{target}' && els[i].childElementCount === 0) {{
                    var r = els[i].getBoundingClientRect();
                    if (r.x > 700 && r.y < 80 && r.width < 120) {{
                        els[i].click();
                        return 'ok';
                    }}
                }}
            }}
            return null;
        }})()
        """)
        if result == "ok":
            time.sleep(0.5)
            return {"ok": True, "action": "switch_panel_tab", "tab": target}
        return {"ok": False, "error": f"Tab '{target}' not found in panel"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_export_setting(format: str = "PNG", scale: str = "1x",
                       port: int = CDP_PORT) -> Dict[str, Any]:
    """Add an export setting to the currently selected element."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        plus = cdp.evaluate("""
        (function() {
            var els = document.querySelectorAll('*');
            for (var i = 0; i < els.length; i++) {
                if (els[i].textContent.trim() === 'Export' && els[i].childElementCount <= 1) {
                    var parent = els[i].closest('[class]');
                    if (parent) {
                        var btns = parent.querySelectorAll('button');
                        for (var j = 0; j < btns.length; j++) {
                            var r = btns[j].getBoundingClientRect();
                            if (r.width > 0) { btns[j].click(); return 'ok'; }
                        }
                    }
                }
            }
            return null;
        })()
        """)
        if plus == "ok":
            time.sleep(0.5)
            return {"ok": True, "action": "add_export_setting", "format": format, "scale": scale}
        return {"ok": False, "error": "Export section not found (select an element first)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_panel_properties(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read all visible property values from the right panel."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        props = cdp.evaluate("""
        (function() {
            var result = {};
            var inputs = document.querySelectorAll('input');
            for (var i = 0; i < inputs.length; i++) {
                var r = inputs[i].getBoundingClientRect();
                if (r.x > 700 && r.width > 0 && r.height > 0) {
                    var label = inputs[i].getAttribute('aria-label')
                             || inputs[i].getAttribute('data-label')
                             || inputs[i].placeholder
                             || ('input_' + i);
                    if (inputs[i].value) result[label] = inputs[i].value;
                }
            }
            return JSON.stringify(result);
        })()
        """)
        return {"ok": True, "action": "get_panel_properties", "properties": json.loads(props or "{}")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_quick_actions(query: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """Open Figma Quick Actions (Cmd+/) and optionally search."""
    cdp = _ensure_session(port)
    if not cdp:
        return {"ok": False, "error": "No session"}
    try:
        cdp.evaluate("document.querySelector('canvas').focus()")
        time.sleep(0.2)
        cdp.send_and_recv("Input.dispatchKeyEvent", {
            "type": "rawKeyDown", "key": "/", "code": "Slash",
            "windowsVirtualKeyCode": 191, "nativeVirtualKeyCode": 191,
            "modifiers": 4
        })
        time.sleep(0.05)
        cdp.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "/", "code": "Slash",
            "windowsVirtualKeyCode": 191, "nativeVirtualKeyCode": 191,
            "modifiers": 0
        })
        time.sleep(0.8)
        if query:
            from interface.chrome import insert_text
            for ch in query:
                insert_text(cdp, ch)
                time.sleep(0.03)
            time.sleep(0.5)
        return {"ok": True, "action": "open_quick_actions", "query": query}
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
