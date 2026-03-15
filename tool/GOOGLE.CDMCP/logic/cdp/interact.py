"""CDMCP Interaction Interfaces — High-level MCP operations with visual effects.

Provides generic interfaces that combine overlay highlighting with actual
CDP interactions (click, type, scroll). Each operation follows the pattern:
  1. Highlight the target element (visual cue)
  2. Hold the highlight for a configurable dwell time
  3. Perform the actual interaction via CDP
  4. Remove the highlight

These interfaces ensure consistent visual feedback across all MCP tools.
"""

import json
import time
from typing import Optional, Dict, Any

from logic.chrome.session import (
    CDPSession, real_click, insert_text,
)

import importlib.util
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"
_SESSION_MGR_PATH = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"

_overlay_mod = None
_session_mgr_mod = None


def _overlay():
    global _overlay_mod
    if _overlay_mod is None:
        spec = importlib.util.spec_from_file_location("cdmcp_overlay", str(_OVERLAY_PATH))
        _overlay_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_overlay_mod)
    return _overlay_mod


def _session_mgr():
    """Lazily load and cache the session manager module."""
    global _session_mgr_mod
    if _session_mgr_mod is not None:
        return _session_mgr_mod
    try:
        import sys as _sys
        _mod_name = "cdmcp_sessions"
        if _mod_name in _sys.modules:
            _session_mgr_mod = _sys.modules[_mod_name]
        else:
            spec = importlib.util.spec_from_file_location(
                _mod_name, str(_SESSION_MGR_PATH))
            _session_mgr_mod = importlib.util.module_from_spec(spec)
            _sys.modules[_mod_name] = _session_mgr_mod
            spec.loader.exec_module(_session_mgr_mod)
    except Exception:
        pass
    return _session_mgr_mod


def _touch_session(session: CDPSession):
    """Touch the owning CDMCPSession so MCP operations reset the idle timer."""
    mgr = _session_mgr()
    if mgr:
        try:
            mgr.touch_by_cdp(session)
        except Exception:
            pass


def _ensure_locked(session: CDPSession, tool_name: str = "CDMCP"):
    """Auto-lock the tab if not already locked, restoring the persistent MPC count."""
    ov = _overlay()
    if not ov.is_locked(session):
        ov.inject_lock(session, base_opacity=0.08, flash_opacity=0.25,
                       tool_name=tool_name)
        mgr = _session_mgr()
        if mgr:
            try:
                count = mgr.get_mcp_count_by_cdp(session)
                if count > 0:
                    session.evaluate(
                        f"window.__cdmcp_mcp_count__ = {count};"
                        " if (window.__cdmcp_update_timer__)"
                        " window.__cdmcp_update_timer__();")
            except Exception:
                pass


def _was_unlocked(session: CDPSession) -> bool:
    """Check if the user unlocked the tab during an operation."""
    try:
        return _overlay().is_locked(session) is not True
    except Exception:
        return False


def _update_cursor(session: CDPSession, x: int, y: int):
    """Update cursor position on the overlay badge and dot."""
    try:
        _overlay().update_cursor_position(session, x, y)
    except Exception:
        pass


def _count_mcp_op(session: CDPSession):
    """Increment MPC counter only if the tab is still locked (not user-interrupted)."""
    if _was_unlocked(session):
        return
    mgr = _session_mgr()
    if mgr:
        try:
            mgr.increment_mcp_count_by_cdp(session)
        except Exception:
            pass
    try:
        _overlay().increment_mcp_count(session, 1)
    except Exception:
        pass


def mcp_click(session: CDPSession, selector: str,
              label: str = "", dwell: float = 1.0,
              color: str = "#e8710a",
              unlock_for_click: bool = True,
              tool_name: str = "CDMCP",
              require_lock: bool = True) -> Dict[str, Any]:
    """Highlight an element, hold the highlight, then click it.

    Args:
        session: Active CDP session.
        selector: CSS selector for the target element.
        label: Label shown on the highlight overlay.
        dwell: Seconds to hold the highlight before clicking.
        color: Highlight border color.
        unlock_for_click: If locked, temporarily allow clicks through.
        tool_name: Name shown in lock label (e.g. "GCS").
        require_lock: If True, auto-lock tab before interaction.

    Returns dict with 'ok', 'clicked', 'rect', 'element' keys.
    """
    _touch_session(session)
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)
    if not label:
        label = selector

    hl = ov.inject_highlight(session, selector, label=label, color=color)
    if not hl.get("ok"):
        return hl

    time.sleep(dwell)

    rect = hl.get("rect", {})
    if not rect:
        ov.remove_highlight(session)
        return {"ok": False, "error": "No rect for element", "element": hl.get("element")}

    cx = rect["left"] + rect["width"] / 2
    cy = rect["top"] + rect["height"] / 2

    try:
        if unlock_for_click:
            ov.set_lock_passthrough(session, True)

        ov.remove_highlight(session)
        _update_cursor(session, cx, cy)
        real_click(session, cx, cy)
    finally:
        if unlock_for_click:
            ov.set_lock_passthrough(session, False)

    if _was_unlocked(session):
        return {"ok": False, "error": "User unlocked during operation",
                "interrupted": True}
    _count_mcp_op(session)
    return {
        "ok": True,
        "clicked": True,
        "selector": selector,
        "rect": rect,
        "element": hl.get("element", {}),
    }


def mcp_type(session: CDPSession, selector: str, text: str,
             label: str = "", char_delay: float = 0.04,
             color: str = "#1a73e8",
             focus_first: bool = True,
             clear_first: bool = False,
             manage_passthrough: bool = True,
             tool_name: str = "CDMCP",
             require_lock: bool = True) -> Dict[str, Any]:
    """Highlight an input element, then type text character by character.

    Args:
        session: Active CDP session.
        selector: CSS selector for the input/textarea.
        text: Text to type.
        label: Label shown on the highlight overlay.
        char_delay: Delay between each character (typing speed).
        color: Highlight border color.
        focus_first: Whether to focus the element before typing.
        clear_first: Whether to clear existing text before typing.
        manage_passthrough: If True, temporarily enables lock passthrough
            during typing and restores it after. Set False when the
            caller manages passthrough externally.
        tool_name: Name shown in lock label (e.g. "GCS").
        require_lock: If True, auto-lock tab before interaction.

    Returns dict with 'ok', 'typed', 'length' keys.
    """
    _touch_session(session)
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)
    if not label:
        label = f"Typing: {text[:30]}{'...' if len(text) > 30 else ''}"

    hl = ov.inject_highlight(session, selector, label=label, color=color)
    if not hl.get("ok"):
        return hl

    time.sleep(0.3)

    try:
        if manage_passthrough:
            ov.set_lock_passthrough(session, True)

        if focus_first:
            session.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
            time.sleep(0.15)

        if clear_first:
            session.evaluate(f"""
                (function() {{
                    var el = document.querySelector({json.dumps(selector)});
                    if (el) {{ el.value = ''; el.dispatchEvent(new Event('input')); }}
                }})()
            """)
            time.sleep(0.1)

        for char in text:
            if _was_unlocked(session):
                break
            insert_text(session, char)
            time.sleep(char_delay)
    finally:
        if manage_passthrough:
            ov.set_lock_passthrough(session, False)
        ov.remove_highlight(session)

    if _was_unlocked(session):
        return {"ok": False, "error": "User unlocked during operation",
                "interrupted": True}
    _count_mcp_op(session)
    return {
        "ok": True,
        "typed": True,
        "text": text,
        "length": len(text),
        "selector": selector,
    }


def mcp_scroll(session: CDPSession, direction: str = "down",
               amount: int = 300,
               smooth: bool = True) -> Dict[str, Any]:
    """Scroll the page with a brief visual indicator.

    Args:
        direction: 'up' or 'down'.
        amount: Pixels to scroll.
        smooth: Use smooth scrolling.
    """
    _touch_session(session)
    dy = amount if direction == "down" else -amount
    behavior = "smooth" if smooth else "auto"

    session.evaluate(f"window.scrollBy({{top: {dy}, behavior: '{behavior}'}})")
    time.sleep(0.3 if smooth else 0.1)

    _count_mcp_op(session)
    return {"ok": True, "direction": direction, "amount": amount}


def mcp_paste(session: CDPSession, text: str,
              selector: str = "",
              label: str = "",
              color: str = "#1a73e8",
              tool_name: str = "CDMCP",
              require_lock: bool = True) -> Dict[str, Any]:
    """Set clipboard content and simulate paste (Cmd+V / Ctrl+V).

    This writes *text* to the clipboard via CDP, optionally focuses the
    target element, then dispatches the paste keyboard shortcut. Useful
    for large text that would be too slow to type character-by-character.

    Args:
        session: Active CDP session.
        text: Text to paste.
        selector: Optional CSS selector for the target element to focus first.
        label: Label shown on the highlight overlay.
        color: Highlight color.
        tool_name: Name for lock label.
        require_lock: Auto-lock before interaction.
    """
    import platform
    _touch_session(session)
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)

    if selector:
        if not label:
            label = f"Paste: {text[:30]}{'...' if len(text) > 30 else ''}"
        ov.inject_highlight(session, selector, label=label, color=color)
        time.sleep(0.3)
        session.evaluate(f"document.querySelector({json.dumps(selector)}).focus()")
        time.sleep(0.15)

    try:
        ov.set_lock_passthrough(session, True)

        session.send_and_recv("Runtime.evaluate", {
            "expression": f"navigator.clipboard.writeText({json.dumps(text)})",
            "awaitPromise": True,
        })
        time.sleep(0.1)

        mod_key = "Meta" if platform.system() == "Darwin" else "Control"
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": mod_key, "code": f"{mod_key}Left",
            "modifiers": 4 if mod_key == "Meta" else 2,
        })
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": "v", "code": "KeyV",
            "text": "v",
            "modifiers": 4 if mod_key == "Meta" else 2,
        })
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": "v", "code": "KeyV",
            "modifiers": 4 if mod_key == "Meta" else 2,
        })
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": mod_key, "code": f"{mod_key}Left",
        })
    finally:
        ov.set_lock_passthrough(session, False)
        time.sleep(0.2)

        if selector:
            ov.remove_highlight(session)

    _count_mcp_op(session)
    return {"ok": True, "pasted": True, "text": text, "length": len(text)}


def mcp_wait_and_click(session: CDPSession, selector: str,
                       label: str = "", timeout: float = 10.0,
                       dwell: float = 1.0, poll_interval: float = 0.5,
                       color: str = "#e8710a",
                       tool_name: str = "CDMCP",
                       require_lock: bool = True) -> Dict[str, Any]:
    """Wait for an element to appear, then highlight and click it.

    Polls until the element is found or timeout expires.
    """
    _touch_session(session)
    if require_lock:
        _ensure_locked(session, tool_name)
    deadline = time.time() + timeout
    while time.time() < deadline:
        exists = session.evaluate(
            f"!!document.querySelector({json.dumps(selector)})"
        )
        if exists:
            return mcp_click(session, selector, label=label, dwell=dwell, color=color)
        time.sleep(poll_interval)

    return {"ok": False, "error": f"Element not found within {timeout}s: {selector}"}


def mcp_navigate(session: CDPSession, url: str,
                 wait_selector: Optional[str] = None,
                 timeout: float = 10.0,
                 tool_name: str = "CDMCP",
                 require_lock: bool = True) -> Dict[str, Any]:
    """Navigate to a URL and optionally wait for an element.

    Args:
        session: Active CDP session.
        url: URL to navigate to.
        wait_selector: CSS selector to wait for after navigation.
        timeout: Max seconds to wait for the selector.
        tool_name: Name shown in lock label.
        require_lock: If True, auto-lock tab before interaction.
    """
    _touch_session(session)
    session.evaluate(f"window.location.href = {json.dumps(url)}")

    if wait_selector:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.5)
            found = session.evaluate(
                f"!!document.querySelector({json.dumps(wait_selector)})"
            )
            if found:
                break
        else:
            if require_lock:
                _ensure_locked(session, tool_name)
            _count_mcp_op(session)
            return {"ok": True, "url": url, "element_found": False, "timeout": True}
    else:
        time.sleep(2)

    if require_lock:
        _ensure_locked(session, tool_name)
    _count_mcp_op(session)
    return {"ok": True, "url": url,
            **({"element_found": True} if wait_selector else {})}


def mcp_drag(session: CDPSession,
             x1: int, y1: int, x2: int, y2: int,
             steps: int = 15,
             label: str = "",
             color: str = "#e8710a",
             tool_name: str = "CDMCP",
             require_lock: bool = True) -> Dict[str, Any]:
    """Perform a smooth mouse drag from (x1,y1) to (x2,y2) with visual indicator.

    Auto-locks, enables passthrough during drag, and counts as one MPC operation.

    Args:
        session: Active CDP session.
        x1, y1: Start viewport coordinates.
        x2, y2: End viewport coordinates.
        steps: Number of intermediate mouseMoved events for smoothness.
        label: Optional label for the overlay badge shown during drag.
        color: Overlay badge color.
        tool_name: Name for lock label.
        require_lock: Auto-lock before interaction.
    """
    _touch_session(session)
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)

    try:
        ov.set_lock_passthrough(session, True)

        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseMoved", "x": x1, "y": y1})
        time.sleep(0.05)
        _update_cursor(session, x1, y1)
        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": x1, "y": y1,
            "button": "left", "clickCount": 1, "buttons": 1})
        time.sleep(0.05)

        for i in range(1, steps + 1):
            frac = i / steps
            mx = int(x1 + (x2 - x1) * frac)
            my = int(y1 + (y2 - y1) * frac)
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": mx, "y": my,
                "button": "left", "buttons": 1})
            time.sleep(0.02)

        _update_cursor(session, x2, y2)
        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": x2, "y": y2,
            "button": "left", "clickCount": 1, "buttons": 0})
    finally:
        ov.set_lock_passthrough(session, False)

    if _was_unlocked(session):
        return {"ok": False, "error": "User unlocked during drag",
                "interrupted": True}
    _count_mcp_op(session)
    return {"ok": True, "action": "drag",
            "from": {"x": x1, "y": y1}, "to": {"x": x2, "y": y2}}
