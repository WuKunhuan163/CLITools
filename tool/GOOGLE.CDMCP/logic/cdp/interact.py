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

from interface.chrome import (
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
        tool_name: Name shown in lock label (e.g. "GDS").
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
        tool_name: Name shown in lock label (e.g. "GDS").
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


# ─── Accessibility & State Queries ──────────────────────────────────────────

def mcp_snapshot(session: CDPSession,
                 interactive_only: bool = False,
                 selector: str = "",
                 max_depth: int = 20) -> Dict[str, Any]:
    """Capture an accessibility tree snapshot of the page.

    Inspired by Cursor's browser_snapshot — returns a structured
    representation of the page content that's more useful than
    screenshots for understanding page structure.

    Args:
        session: Active CDP session.
        interactive_only: If True, only include interactive elements.
        selector: CSS selector to scope the snapshot subtree.
        max_depth: Maximum depth to traverse.
    """
    _touch_session(session)
    js = f"""
    (function() {{
        function walk(el, depth) {{
            if (depth > {max_depth}) return null;
            var tag = el.tagName ? el.tagName.toLowerCase() : '';
            var role = el.getAttribute ? (el.getAttribute('role') || '') : '';
            var ariaLabel = el.getAttribute ? (el.getAttribute('aria-label') || '') : '';
            var text = '';
            if (el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {{
                text = el.childNodes[0].textContent.trim().slice(0, 200);
            }}
            var interactive = ['a','button','input','select','textarea'].includes(tag)
                || role === 'button' || role === 'link' || role === 'textbox'
                || (el.getAttribute && el.getAttribute('contenteditable') === 'true')
                || (el.getAttribute && el.getAttribute('tabindex'));
            if ({str(interactive_only).lower()} && !interactive && depth > 2) {{
                var kids = [];
                for (var i = 0; i < el.children.length; i++) {{
                    var c = walk(el.children[i], depth + 1);
                    if (c) kids.push(c);
                }}
                if (kids.length === 0) return null;
                if (kids.length === 1) return kids[0];
                return {{ tag: '...', children: kids }};
            }}
            var node = {{ tag: tag }};
            if (role) node.role = role;
            if (ariaLabel) node.label = ariaLabel;
            if (text) node.text = text;
            if (el.id) node.id = el.id;
            if (el.className && typeof el.className === 'string')
                node.cls = el.className.split(' ').filter(Boolean).slice(0, 5).join(' ');
            if (tag === 'input') {{
                node.type = el.type || 'text';
                node.value = el.value || '';
                node.name = el.name || '';
            }}
            if (tag === 'select') {{
                node.value = el.value || '';
                node.options = Array.from(el.options).slice(0, 20).map(
                    o => ({{ value: o.value, label: o.textContent.trim(), selected: o.selected }}));
            }}
            if (tag === 'a') node.href = (el.href || '').slice(0, 200);
            if (tag === 'img') node.alt = el.alt || '';
            if (el.disabled) node.disabled = true;
            if (el.checked) node.checked = true;
            var kids = [];
            for (var i = 0; i < el.children.length && i < 100; i++) {{
                var c = walk(el.children[i], depth + 1);
                if (c) kids.push(c);
            }}
            if (kids.length > 0) node.children = kids;
            return node;
        }}
        var root = {f'document.querySelector({json.dumps(selector)})' if selector else 'document.body'};
        if (!root) return JSON.stringify({{ ok: false, error: 'Root element not found' }});
        return JSON.stringify({{ ok: true, tree: walk(root, 0),
            url: location.href, title: document.title }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=10)
        if isinstance(raw, str):
            return json.loads(raw)
        return {"ok": False, "error": "Unexpected eval result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_is_visible(session: CDPSession, selector: str) -> Dict[str, Any]:
    """Check if an element is visible in the viewport."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        var r = el.getBoundingClientRect();
        var style = getComputedStyle(el);
        var visible = r.width > 0 && r.height > 0
            && style.visibility !== 'hidden' && style.display !== 'none'
            && parseFloat(style.opacity) > 0;
        var inViewport = r.top < window.innerHeight && r.bottom > 0
            && r.left < window.innerWidth && r.right > 0;
        return JSON.stringify({{ ok: true, visible: visible, in_viewport: inViewport,
            rect: {{ top: r.top, left: r.left, width: r.width, height: r.height }} }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_is_enabled(session: CDPSession, selector: str) -> Dict[str, Any]:
    """Check if an element is enabled (not disabled)."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        var disabled = el.disabled === true;
        var fs = el.closest('fieldset[disabled]');
        return JSON.stringify({{ ok: true, enabled: !disabled && !fs }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_is_checked(session: CDPSession, selector: str) -> Dict[str, Any]:
    """Check if a checkbox or radio element is checked."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        return JSON.stringify({{ ok: true, checked: !!el.checked }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_get_attribute(session: CDPSession, selector: str,
                      attribute: str) -> Dict[str, Any]:
    """Read a specific attribute from an element."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        var val = el.getAttribute({json.dumps(attribute)});
        return JSON.stringify({{ ok: true, attribute: {json.dumps(attribute)}, value: val }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_get_input_value(session: CDPSession, selector: str) -> Dict[str, Any]:
    """Read the current value of an input, textarea, or contenteditable element."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        if (el.isContentEditable) return JSON.stringify({{ ok: true, value: el.textContent }});
        if (el.type === 'password') return JSON.stringify({{ ok: true, value: '***' }});
        return JSON.stringify({{ ok: true, value: el.value || '' }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_get_bounding_box(session: CDPSession, selector: str) -> Dict[str, Any]:
    """Get the bounding box of an element."""
    _touch_session(session)
    js = f"""
    (function() {{
        var el = document.querySelector({json.dumps(selector)});
        if (!el) return JSON.stringify({{ ok: false, error: 'Element not found' }});
        var r = el.getBoundingClientRect();
        return JSON.stringify({{ ok: true, rect: {{
            x: r.x, y: r.y, width: r.width, height: r.height,
            top: r.top, right: r.right, bottom: r.bottom, left: r.left
        }} }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Navigation ─────────────────────────────────────────────────────────────

def mcp_navigate_back(session: CDPSession) -> Dict[str, Any]:
    """Go back in browser history."""
    _touch_session(session)
    try:
        result = session.evaluate("history.length")
        session.evaluate("history.back()")
        time.sleep(1)
        url = session.evaluate("location.href")
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_navigate_forward(session: CDPSession) -> Dict[str, Any]:
    """Go forward in browser history."""
    _touch_session(session)
    try:
        session.evaluate("history.forward()")
        time.sleep(1)
        url = session.evaluate("location.href")
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_reload(session: CDPSession, wait: float = 2.0) -> Dict[str, Any]:
    """Reload the current page."""
    _touch_session(session)
    try:
        session.send_and_recv("Page.reload", {"ignoreCache": False}, timeout=10)
        time.sleep(wait)
        url = session.evaluate("location.href")
        return {"ok": True, "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Form Interactions ──────────────────────────────────────────────────────

def mcp_fill(session: CDPSession, selector: str, value: str,
             tool_name: str = "CDMCP",
             require_lock: bool = True) -> Dict[str, Any]:
    """Clear and atomically set a value on an input element.

    Unlike mcp_type which types character-by-character, this replaces the
    entire value at once — faster for large text or when keystroke events
    don't matter.
    """
    _touch_session(session)
    if require_lock:
        _ensure_locked(session, tool_name)
    ov = _overlay()
    hl = ov.inject_highlight(session, selector,
                             label=f"Fill: {value[:30]}...",
                             color="#1a73e8")
    if not hl.get("ok"):
        return hl
    time.sleep(0.3)
    try:
        ov.set_lock_passthrough(session, True)
        session.evaluate(f"""
            (function() {{
                var el = document.querySelector({json.dumps(selector)});
                if (!el) return;
                el.focus();
                el.value = {json.dumps(value)};
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }})()
        """)
    finally:
        ov.set_lock_passthrough(session, False)
        ov.remove_highlight(session)
    _count_mcp_op(session)
    return {"ok": True, "filled": True, "selector": selector, "length": len(value)}


def mcp_fill_form(session: CDPSession, fields: list,
                  tool_name: str = "CDMCP",
                  require_lock: bool = True) -> Dict[str, Any]:
    """Fill multiple form fields at once.

    Args:
        fields: List of dicts with 'selector' and 'value' keys,
                optionally 'clear' (default True).
    """
    _touch_session(session)
    if require_lock:
        _ensure_locked(session, tool_name)
    results = []
    for field in fields:
        sel = field.get("selector", "")
        val = field.get("value", "")
        clear = field.get("clear", True)
        if not sel:
            results.append({"ok": False, "error": "Missing selector"})
            continue
        try:
            js = f"""
            (function() {{
                var el = document.querySelector({json.dumps(sel)});
                if (!el) return 'not_found';
                el.focus();
                {"el.value = '';" if clear else ""}
                el.value = {json.dumps(val)};
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return 'ok';
            }})()
            """
            r = session.evaluate(js, timeout=5)
            results.append({"ok": r == "ok", "selector": sel})
        except Exception as e:
            results.append({"ok": False, "selector": sel, "error": str(e)})
    _count_mcp_op(session)
    return {"ok": True, "fields": results}


def mcp_select_option(session: CDPSession, selector: str,
                      values: list,
                      tool_name: str = "CDMCP",
                      require_lock: bool = True) -> Dict[str, Any]:
    """Select options in a <select> dropdown.

    Args:
        values: List of values or labels to select.
    """
    _touch_session(session)
    if require_lock:
        _ensure_locked(session, tool_name)
    ov = _overlay()
    hl = ov.inject_highlight(session, selector, label="Select option", color="#1a73e8")
    time.sleep(0.3)
    try:
        js = f"""
        (function() {{
            var el = document.querySelector({json.dumps(selector)});
            if (!el || el.tagName !== 'SELECT') return JSON.stringify({{ ok: false, error: 'Not a select' }});
            var vals = {json.dumps(values)};
            var matched = [];
            for (var i = 0; i < el.options.length; i++) {{
                var opt = el.options[i];
                for (var v of vals) {{
                    if (opt.value === v || opt.textContent.trim() === v
                        || opt.textContent.trim().toLowerCase().includes(v.toLowerCase())) {{
                        opt.selected = true;
                        matched.push({{ value: opt.value, label: opt.textContent.trim() }});
                        break;
                    }}
                }}
            }}
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            return JSON.stringify({{ ok: true, matched: matched }});
        }})()
        """
        raw = session.evaluate(js, timeout=5)
        result = json.loads(raw) if isinstance(raw, str) else {"ok": False}
    finally:
        ov.remove_highlight(session)
    _count_mcp_op(session)
    return result


def mcp_hover(session: CDPSession, selector: str,
              label: str = "", dwell: float = 0.5,
              color: str = "#e8710a",
              tool_name: str = "CDMCP",
              require_lock: bool = True) -> Dict[str, Any]:
    """Hover over an element with visual highlight."""
    _touch_session(session)
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)
    if not label:
        label = selector
    hl = ov.inject_highlight(session, selector, label=label, color=color)
    if not hl.get("ok"):
        return hl
    rect = hl.get("rect", {})
    if rect:
        cx = rect["left"] + rect["width"] / 2
        cy = rect["top"] + rect["height"] / 2
        try:
            ov.set_lock_passthrough(session, True)
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": int(cx), "y": int(cy)})
            _update_cursor(session, cx, cy)
        finally:
            ov.set_lock_passthrough(session, False)
    time.sleep(dwell)
    ov.remove_highlight(session)
    _count_mcp_op(session)
    return {"ok": True, "hovered": True, "selector": selector, "rect": rect}


# ─── Keyboard ───────────────────────────────────────────────────────────────

_KEY_CODES = {
    "Enter": 13, "Tab": 9, "Escape": 27, "Backspace": 8, "Delete": 46,
    "ArrowUp": 38, "ArrowDown": 40, "ArrowLeft": 37, "ArrowRight": 39,
    "PageUp": 33, "PageDown": 34, "Home": 36, "End": 35, "Space": 32,
    "F1": 112, "F2": 113, "F3": 114, "F4": 115, "F5": 116, "F6": 117,
    "F7": 118, "F8": 119, "F9": 120, "F10": 121, "F11": 122, "F12": 123,
}

_MODIFIER_MAP = {
    "Control": 2, "Ctrl": 2,
    "Shift": 8, "Alt": 1, "Option": 1,
    "Meta": 4, "Command": 4, "Cmd": 4, "Win": 4,
}


def mcp_press_key(session: CDPSession, key: str) -> Dict[str, Any]:
    """Press a key or key combination (e.g. 'Enter', 'Control+s', 'Meta+a').

    Supports modifier syntax with '+' separator.
    """
    _touch_session(session)
    parts = [k.strip() for k in key.split("+")]
    modifiers = 0
    actual_key = parts[-1]
    for mod in parts[:-1]:
        modifiers |= _MODIFIER_MAP.get(mod, 0)

    code = actual_key
    if len(actual_key) == 1:
        code = f"Key{actual_key.upper()}"
    key_code = _KEY_CODES.get(actual_key, ord(actual_key.upper()) if len(actual_key) == 1 else 0)

    try:
        for mod in parts[:-1]:
            session.send_and_recv("Input.dispatchKeyEvent", {
                "type": "keyDown", "key": mod, "modifiers": modifiers})

        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyDown", "key": actual_key, "code": code,
            "windowsVirtualKeyCode": key_code,
            "text": actual_key if len(actual_key) == 1 and not modifiers else "",
            "modifiers": modifiers})
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": "keyUp", "key": actual_key, "code": code,
            "windowsVirtualKeyCode": key_code, "modifiers": modifiers})

        for mod in reversed(parts[:-1]):
            session.send_and_recv("Input.dispatchKeyEvent", {
                "type": "keyUp", "key": mod})

        return {"ok": True, "key": key}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Monitoring ─────────────────────────────────────────────────────────────

def mcp_console_messages(session: CDPSession, limit: int = 100) -> Dict[str, Any]:
    """Capture recent console messages from the page.

    Enables Runtime domain console collection, waits briefly, then returns messages.
    """
    _touch_session(session)
    js = f"""
    (function() {{
        if (!window.__cdmcp_console_log__) {{
            window.__cdmcp_console_log__ = [];
            var orig = {{}};
            ['log','warn','error','info','debug'].forEach(function(m) {{
                orig[m] = console[m];
                console[m] = function() {{
                    var args = Array.from(arguments).map(function(a) {{
                        try {{ return typeof a === 'object' ? JSON.stringify(a) : String(a); }}
                        catch(e) {{ return String(a); }}
                    }});
                    window.__cdmcp_console_log__.push({{ level: m, text: args.join(' '),
                        ts: Date.now() }});
                    if (window.__cdmcp_console_log__.length > 500)
                        window.__cdmcp_console_log__.shift();
                    orig[m].apply(console, arguments);
                }};
            }});
        }}
        return JSON.stringify({{ ok: true,
            messages: window.__cdmcp_console_log__.slice(-{limit}) }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_network_requests(session: CDPSession, limit: int = 100) -> Dict[str, Any]:
    """Capture recent network requests using Performance API.

    Returns resource timing entries from the page's performance buffer.
    """
    _touch_session(session)
    js = f"""
    (function() {{
        var entries = performance.getEntriesByType('resource').slice(-{limit});
        var requests = entries.map(function(e) {{
            return {{
                name: e.name,
                type: e.initiatorType,
                duration: Math.round(e.duration),
                size: e.transferSize || 0,
                start: Math.round(e.startTime),
            }};
        }});
        return JSON.stringify({{ ok: true, requests: requests, count: entries.length }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Page Search ────────────────────────────────────────────────────────────

def mcp_search(session: CDPSession, query: str,
               case_sensitive: bool = False) -> Dict[str, Any]:
    """Search for text on the page, similar to Cmd+F.

    Returns match count and scrolls to the first match.
    """
    _touch_session(session)
    flags = "" if case_sensitive else "gi"
    js = f"""
    (function() {{
        if (window.__cdmcp_search_hl__) {{
            window.__cdmcp_search_hl__.forEach(function(el) {{
                var parent = el.parentNode;
                parent.replaceChild(document.createTextNode(el.textContent), el);
                parent.normalize();
            }});
        }}
        window.__cdmcp_search_hl__ = [];
        var query = {json.dumps(query)};
        if (!query) return JSON.stringify({{ ok: true, matches: 0 }});
        var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
        var matches = 0;
        var firstMatch = null;
        var regex = new RegExp(query.replace(/[.*+?^${{}}()|[\\]\\\\]/g, '\\\\$&'), '{flags}');
        var nodes = [];
        while (walker.nextNode()) nodes.push(walker.currentNode);
        nodes.forEach(function(node) {{
            if (!regex.test(node.textContent)) return;
            var frag = document.createDocumentFragment();
            var text = node.textContent;
            var last = 0;
            regex.lastIndex = 0;
            var m;
            while ((m = regex.exec(text)) !== null) {{
                if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
                var span = document.createElement('span');
                span.style.cssText = 'background:#ff0;outline:2px solid #f90;border-radius:2px;';
                span.textContent = m[0];
                window.__cdmcp_search_hl__.push(span);
                if (!firstMatch) firstMatch = span;
                frag.appendChild(span);
                matches++;
                last = m.index + m[0].length;
                if (!regex.global) break;
            }}
            if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
            node.parentNode.replaceChild(frag, node);
        }});
        if (firstMatch) firstMatch.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        return JSON.stringify({{ ok: true, matches: matches }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=10)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mcp_clear_search(session: CDPSession) -> Dict[str, Any]:
    """Clear search highlights from the page."""
    _touch_session(session)
    js = """
    (function() {
        if (window.__cdmcp_search_hl__) {
            window.__cdmcp_search_hl__.forEach(function(el) {
                var parent = el.parentNode;
                if (parent) {
                    parent.replaceChild(document.createTextNode(el.textContent), el);
                    parent.normalize();
                }
            });
            window.__cdmcp_search_hl__ = [];
        }
        return JSON.stringify({ ok: true });
    })()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Dialog Handling ────────────────────────────────────────────────────────

def mcp_handle_dialog(session: CDPSession, accept: bool = True,
                      prompt_text: str = "") -> Dict[str, Any]:
    """Configure how native dialogs (alert/confirm/prompt) are handled.

    Call BEFORE the action that triggers the dialog.
    """
    _touch_session(session)
    js = f"""
    (function() {{
        window.__cdmcp_dialog_accept__ = {str(accept).lower()};
        window.__cdmcp_dialog_prompt__ = {json.dumps(prompt_text)};
        if (!window.__cdmcp_dialog_patched__) {{
            window.__cdmcp_dialog_patched__ = true;
            window.__cdmcp_dialog_history__ = [];
            var origAlert = window.alert;
            var origConfirm = window.confirm;
            var origPrompt = window.prompt;
            window.alert = function(msg) {{
                window.__cdmcp_dialog_history__.push({{ type: 'alert', message: String(msg), ts: Date.now() }});
            }};
            window.confirm = function(msg) {{
                var accept = window.__cdmcp_dialog_accept__ !== false;
                window.__cdmcp_dialog_history__.push({{ type: 'confirm', message: String(msg),
                    result: accept, ts: Date.now() }});
                return accept;
            }};
            window.prompt = function(msg, def) {{
                var text = window.__cdmcp_dialog_prompt__ || def || '';
                window.__cdmcp_dialog_history__.push({{ type: 'prompt', message: String(msg),
                    result: text, ts: Date.now() }});
                return window.__cdmcp_dialog_accept__ !== false ? text : null;
            }};
        }}
        return JSON.stringify({{ ok: true, accept: {str(accept).lower()},
            history: (window.__cdmcp_dialog_history__ || []).slice(-10) }});
    }})()
    """
    try:
        raw = session.evaluate(js, timeout=5)
        return json.loads(raw) if isinstance(raw, str) else {"ok": False, "error": "Unexpected result"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─── Wait ───────────────────────────────────────────────────────────────────

def mcp_wait_for(session: CDPSession, text: str = "",
                 text_gone: str = "",
                 wait_time: float = 0,
                 timeout: float = 30.0,
                 poll: float = 0.5) -> Dict[str, Any]:
    """Wait for text to appear/disappear or for a fixed duration.

    Args:
        text: Wait for this text to appear on the page.
        text_gone: Wait for this text to disappear.
        wait_time: Fixed wait in seconds (used if no text conditions).
        timeout: Max seconds to wait for text conditions.
        poll: Polling interval in seconds.
    """
    _touch_session(session)
    if wait_time and not text and not text_gone:
        time.sleep(wait_time)
        return {"ok": True, "waited": wait_time}

    deadline = time.time() + timeout
    while time.time() < deadline:
        body_text = session.evaluate("document.body.innerText || ''") or ""
        if text and text in body_text:
            return {"ok": True, "found": text}
        if text_gone and text_gone not in body_text:
            return {"ok": True, "gone": text_gone}
        if not text and not text_gone:
            return {"ok": True}
        time.sleep(poll)

    return {"ok": False, "error": f"Timeout after {timeout}s",
            "text": text, "text_gone": text_gone}


# ─── Screenshot ─────────────────────────────────────────────────────────────

def mcp_screenshot(session: CDPSession, selector: str = "",
                   full_page: bool = False,
                   fmt: str = "png") -> Dict[str, Any]:
    """Capture a screenshot and return base64-encoded image data.

    Args:
        selector: Optional CSS selector to screenshot just one element.
        full_page: If True, capture the full scrollable page.
        fmt: Image format ('png' or 'jpeg').
    """
    import base64 as _b64
    _touch_session(session)
    try:
        params = {"format": fmt}
        if selector:
            js = f"""
            (function() {{
                var el = document.querySelector({json.dumps(selector)});
                if (!el) return null;
                var r = el.getBoundingClientRect();
                return {{ x: r.x, y: r.y, width: r.width, height: r.height, scale: window.devicePixelRatio }};
            }})()
            """
            clip = session.evaluate(js, timeout=5)
            if clip:
                params["clip"] = clip
        elif full_page:
            metrics = session.send_and_recv("Page.getLayoutMetrics", {}, timeout=5)
            content_size = (metrics.get("result", {}).get("contentSize") or
                           metrics.get("result", {}).get("cssContentSize", {}))
            if content_size:
                params["clip"] = {
                    "x": 0, "y": 0,
                    "width": content_size.get("width", 1920),
                    "height": content_size.get("height", 1080),
                    "scale": 1,
                }
        r = session.send_and_recv("Page.captureScreenshot", params, timeout=15)
        data = r.get("result", {}).get("data", "") if r else ""
        if data:
            return {"ok": True, "format": fmt, "data_length": len(data),
                    "data_b64": data[:100] + "..."}
        return {"ok": False, "error": "Empty screenshot data"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
