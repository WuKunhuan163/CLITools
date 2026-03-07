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
    CDPSession, CDP_PORT,
    real_click, insert_text, dispatch_key,
)

import importlib.util
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_OVERLAY_PATH = _TOOL_DIR / "logic" / "cdp" / "overlay.py"

_overlay_mod = None


def _overlay():
    global _overlay_mod
    if _overlay_mod is None:
        spec = importlib.util.spec_from_file_location("cdmcp_overlay", str(_OVERLAY_PATH))
        _overlay_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_overlay_mod)
    return _overlay_mod


def _ensure_locked(session: CDPSession, tool_name: str = "CDMCP"):
    """Auto-lock the tab if not already locked."""
    ov = _overlay()
    if not ov.is_locked(session):
        ov.inject_lock(session, base_opacity=0.08, flash_opacity=0.25,
                       tool_name=tool_name)


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

    if unlock_for_click:
        ov.set_lock_passthrough(session, True)

    ov.remove_highlight(session)
    real_click(session, cx, cy)

    if unlock_for_click:
        ov.set_lock_passthrough(session, False)

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
    ov = _overlay()
    if require_lock:
        _ensure_locked(session, tool_name)
    if not label:
        label = f"Typing: {text[:30]}{'...' if len(text) > 30 else ''}"

    hl = ov.inject_highlight(session, selector, label=label, color=color)
    if not hl.get("ok"):
        return hl

    time.sleep(0.3)

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
        insert_text(session, char)
        time.sleep(char_delay)

    if manage_passthrough:
        ov.set_lock_passthrough(session, False)
    ov.remove_highlight(session)

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
    dy = amount if direction == "down" else -amount
    behavior = "smooth" if smooth else "auto"

    session.evaluate(f"window.scrollBy({{top: {dy}, behavior: '{behavior}'}})")
    time.sleep(0.3 if smooth else 0.1)

    return {"ok": True, "direction": direction, "amount": amount}


def mcp_wait_and_click(session: CDPSession, selector: str,
                       label: str = "", timeout: float = 10.0,
                       dwell: float = 1.0, poll_interval: float = 0.5,
                       color: str = "#e8710a",
                       tool_name: str = "CDMCP",
                       require_lock: bool = True) -> Dict[str, Any]:
    """Wait for an element to appear, then highlight and click it.

    Polls until the element is found or timeout expires.
    """
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
    if require_lock:
        _ensure_locked(session, tool_name)
    session.evaluate(f"window.location.href = {json.dumps(url)}")

    if wait_selector:
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(0.5)
            found = session.evaluate(
                f"!!document.querySelector({json.dumps(wait_selector)})"
            )
            if found:
                return {"ok": True, "url": url, "element_found": True}
        return {"ok": True, "url": url, "element_found": False, "timeout": True}

    time.sleep(2)
    return {"ok": True, "url": url}
