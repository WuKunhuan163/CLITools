"""CDP Overlay System — Visual indicators for agent-controlled browser tabs.

Injects CSS/JS overlays via CDP Runtime.evaluate to provide:
  - Tab group badge: persistent tag marking agent-controlled tabs
  - Focus indicator: border glow on the active debug tab
  - Lock overlay: semi-transparent shade with click-to-unlock badge
  - Element highlight: outline + label on the currently targeted element

This module is service-agnostic and can be used by any CDMCP tool.
"""

import json
import time
from typing import Optional, Dict, Any

from logic.chrome.session import (
    CDPSession, CDP_PORT, CDP_TIMEOUT,
    is_chrome_cdp_available, list_tabs, find_tab, open_tab,
)

CDMCP_OVERLAY_ID = "__cdmcp_overlay_root__"
CDMCP_LOCK_ID = "__cdmcp_lock_overlay__"
CDMCP_BADGE_ID = "__cdmcp_agent_badge__"
CDMCP_FOCUS_ID = "__cdmcp_focus_border__"
CDMCP_HIGHLIGHT_ID = "__cdmcp_element_highlight__"

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------

def get_session(tab_info: Dict[str, Any]) -> Optional[CDPSession]:
    ws = tab_info.get("webSocketDebuggerUrl")
    if not ws:
        return None
    try:
        return CDPSession(ws)
    except Exception:
        return None


def get_session_for_url(url_pattern: str, port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_tab(url_pattern, port=port)
    if tab:
        return get_session(tab)
    return None


# ---------------------------------------------------------------------------
# Inject agent badge (tab group tag)
# ---------------------------------------------------------------------------

_BADGE_JS = r"""
(function() {
    var existing = document.getElementById('__BADGE_ID__');
    if (existing) { existing.remove(); }
    var badge = document.createElement('div');
    badge.id = '__BADGE_ID__';
    badge.innerHTML = '__BADGE_TEXT__';
    badge.style.cssText = [
        'position: fixed',
        'top: 4px',
        'right: 4px',
        'z-index: 2147483647',
        'background: __BADGE_COLOR__',
        'color: #fff',
        'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
        'font-size: 11px',
        'font-weight: 700',
        'padding: 3px 8px',
        'border-radius: 3px',
        'letter-spacing: 0.5px',
        'pointer-events: none',
        'opacity: 0.85',
        'box-shadow: 0 1px 4px rgba(0,0,0,0.18)',
        'user-select: none',
    ].join('; ');
    document.documentElement.appendChild(badge);
    return 'badge_injected';
})()
""".replace("__BADGE_ID__", CDMCP_BADGE_ID)


def inject_badge(session: CDPSession, text: str = "CDMCP",
                 color: str = "#1a73e8") -> bool:
    """Inject the CDMCP agent badge into the top-right corner."""
    js = _BADGE_JS.replace("__BADGE_TEXT__", text).replace("__BADGE_COLOR__", color)
    result = session.evaluate(js)
    return result == "badge_injected"


def remove_badge(session: CDPSession) -> bool:
    js = f"""
    (function() {{
        var el = document.getElementById('{CDMCP_BADGE_ID}');
        if (el) {{ el.remove(); return 'removed'; }}
        return 'not_found';
    }})()
    """
    return session.evaluate(js) == "removed"


# ---------------------------------------------------------------------------
# Focus indicator (border glow)
# ---------------------------------------------------------------------------

_FOCUS_JS = r"""
(function() {
    var existing = document.getElementById('__FOCUS_ID__');
    if (existing) { existing.remove(); }
    var frame = document.createElement('div');
    frame.id = '__FOCUS_ID__';
    frame.style.cssText = [
        'position: fixed',
        'top: 0', 'left: 0', 'right: 0', 'bottom: 0',
        'z-index: 2147483646',
        'pointer-events: none',
        'border: 2px solid __FOCUS_COLOR__',
        'box-shadow: inset 0 0 12px rgba(26, 115, 232, 0.15)',
        'transition: opacity 0.3s ease',
    ].join('; ');
    document.documentElement.appendChild(frame);
    return 'focus_injected';
})()
""".replace("__FOCUS_ID__", CDMCP_FOCUS_ID)


def inject_focus(session: CDPSession, color: str = "#1a73e8") -> bool:
    """Show a focus border indicating the agent is watching this tab."""
    js = _FOCUS_JS.replace("__FOCUS_COLOR__", color)
    result = session.evaluate(js)
    return result == "focus_injected"


def remove_focus(session: CDPSession) -> bool:
    js = f"""
    (function() {{
        var el = document.getElementById('{CDMCP_FOCUS_ID}');
        if (el) {{ el.remove(); return 'removed'; }}
        return 'not_found';
    }})()
    """
    return session.evaluate(js) == "removed"


# ---------------------------------------------------------------------------
# Lock overlay (gray shade + click flash + unlock badge)
# ---------------------------------------------------------------------------

_LOCK_JS_TEMPLATE = r"""
(function() {
    var existing = document.getElementById('__LOCK_ID__');
    if (existing) { existing.remove(); }

    var baseOpacity = __BASE_OPACITY__;
    var flashOpacity = __FLASH_OPACITY__;

    var shade = document.createElement('div');
    shade.id = '__LOCK_ID__';
    shade.style.cssText = [
        'position: fixed',
        'top: 0', 'left: 0', 'right: 0', 'bottom: 0',
        'z-index: 2147483645',
        'background: rgba(0, 0, 0, ' + baseOpacity + ')',
        'transition: background 0.25s ease',
        'cursor: default',
    ].join('; ');

    var label = document.createElement('div');
    label.style.cssText = [
        'position: absolute',
        'top: 50%', 'left: 50%',
        'transform: translate(-50%, -50%)',
        'background: rgba(0, 0, 0, 0.55)',
        'color: #fff',
        'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
        'font-size: 13px',
        'font-weight: 600',
        'padding: 8px 18px',
        'border-radius: 6px',
        'user-select: none',
        'cursor: pointer',
        'letter-spacing: 0.3px',
    ].join('; ');
    label.textContent = 'Locked by CDMCP  |  Click to unlock';
    label.title = 'Click to unlock this tab';

    shade.addEventListener('mousedown', function(e) {
        if (e.target === label) return;
        shade.style.background = 'rgba(0, 0, 0, ' + flashOpacity + ')';
        setTimeout(function() {
            shade.style.background = 'rgba(0, 0, 0, ' + baseOpacity + ')';
        }, 300);
    });

    label.addEventListener('click', function(e) {
        e.stopPropagation();
        shade.remove();
        window.__cdmcp_locked__ = false;
        window.dispatchEvent(new CustomEvent('cdmcp-unlock'));
    });

    shade.appendChild(label);
    document.documentElement.appendChild(shade);
    window.__cdmcp_locked__ = true;
    return 'lock_injected';
})()
""".replace("__LOCK_ID__", CDMCP_LOCK_ID)


def inject_lock(session: CDPSession, base_opacity: float = 0.08,
                flash_opacity: float = 0.25) -> bool:
    """Lock the tab with a semi-transparent overlay."""
    js = (_LOCK_JS_TEMPLATE
          .replace("__BASE_OPACITY__", str(base_opacity))
          .replace("__FLASH_OPACITY__", str(flash_opacity)))
    result = session.evaluate(js)
    return result == "lock_injected"


def remove_lock(session: CDPSession) -> bool:
    js = f"""
    (function() {{
        var el = document.getElementById('{CDMCP_LOCK_ID}');
        if (el) {{ el.remove(); window.__cdmcp_locked__ = false; return 'removed'; }}
        return 'not_found';
    }})()
    """
    return session.evaluate(js) == "removed"


def is_locked(session: CDPSession) -> bool:
    return session.evaluate("!!window.__cdmcp_locked__") is True


# ---------------------------------------------------------------------------
# Element highlight (outline + label)
# ---------------------------------------------------------------------------

_HIGHLIGHT_JS_TEMPLATE = r"""
(function() {
    var existing = document.getElementById('__HIGHLIGHT_ID__');
    if (existing) { existing.remove(); }

    var selector = __SELECTOR_JSON__;
    var label = __LABEL_JSON__;
    var hlColor = __HL_COLOR_JSON__;
    var target = document.querySelector(selector);
    if (!target) { return JSON.stringify({ok: false, error: 'Element not found: ' + selector}); }

    var rect = target.getBoundingClientRect();

    var highlight = document.createElement('div');
    highlight.id = '__HIGHLIGHT_ID__';
    highlight.style.cssText = [
        'position: fixed',
        'top: ' + rect.top + 'px',
        'left: ' + rect.left + 'px',
        'width: ' + rect.width + 'px',
        'height: ' + rect.height + 'px',
        'z-index: 2147483644',
        'border: 2px solid ' + hlColor,
        'border-radius: 3px',
        'pointer-events: none',
        'box-shadow: 0 0 8px ' + hlColor + '4d',
        'transition: all 0.2s ease',
    ].join('; ');

    var tag = document.createElement('div');
    tag.style.cssText = [
        'position: absolute',
        'top: -22px', 'left: 0',
        'background: ' + hlColor,
        'color: #fff',
        'font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, monospace',
        'font-size: 10px',
        'font-weight: 600',
        'padding: 2px 6px',
        'border-radius: 2px',
        'white-space: nowrap',
        'pointer-events: none',
        'max-width: 300px',
        'overflow: hidden',
        'text-overflow: ellipsis',
    ].join('; ');
    tag.textContent = label;

    highlight.appendChild(tag);
    document.documentElement.appendChild(highlight);

    var tagName = target.tagName.toLowerCase();
    var inputType = target.getAttribute('type') || '';
    var placeholder = target.getAttribute('placeholder') || '';
    var ariaLabel = target.getAttribute('aria-label') || '';
    var name = target.getAttribute('name') || '';

    return JSON.stringify({
        ok: true,
        selector: selector,
        label: label,
        element: {
            tag: tagName,
            type: inputType,
            placeholder: placeholder,
            ariaLabel: ariaLabel,
            name: name,
            text: (target.textContent || '').substring(0, 100).trim(),
        },
        rect: {top: rect.top, left: rect.left, width: rect.width, height: rect.height}
    });
})()
""".replace("__HIGHLIGHT_ID__", CDMCP_HIGHLIGHT_ID)


def inject_highlight(session: CDPSession, selector: str,
                     label: str = "",
                     color: str = "#e8710a") -> Dict[str, Any]:
    """Highlight a specific element by CSS selector with an optional label."""
    if not label:
        label = selector
    js = (_HIGHLIGHT_JS_TEMPLATE
          .replace("__SELECTOR_JSON__", json.dumps(selector))
          .replace("__LABEL_JSON__", json.dumps(label))
          .replace("__HL_COLOR_JSON__", json.dumps(color)))
    raw = session.evaluate(js)
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {"ok": False, "error": "No response from overlay injection"}


def remove_highlight(session: CDPSession) -> bool:
    js = f"""
    (function() {{
        var el = document.getElementById('{CDMCP_HIGHLIGHT_ID}');
        if (el) {{ el.remove(); return 'removed'; }}
        return 'not_found';
    }})()
    """
    return session.evaluate(js) == "removed"


# ---------------------------------------------------------------------------
# Composite operations
# ---------------------------------------------------------------------------

def inject_all_overlays(session: CDPSession, locked: bool = False,
                        focus: bool = True,
                        badge_text: str = "CDMCP",
                        badge_color: str = "#1a73e8",
                        focus_color: str = "#1a73e8") -> Dict[str, bool]:
    """Inject badge + optionally focus border and lock overlay."""
    results = {"badge": inject_badge(session, text=badge_text, color=badge_color)}
    if focus:
        results["focus"] = inject_focus(session, color=focus_color)
    if locked:
        results["lock"] = inject_lock(session)
    return results


def remove_all_overlays(session: CDPSession) -> Dict[str, Any]:
    """Remove all CDMCP overlays from the tab."""
    js = f"""
    (function() {{
        var ids = {json.dumps([CDMCP_BADGE_ID, CDMCP_FOCUS_ID, CDMCP_LOCK_ID, CDMCP_HIGHLIGHT_ID])};
        var removed = [];
        ids.forEach(function(id) {{
            var el = document.getElementById(id);
            if (el) {{ el.remove(); removed.push(id); }}
        }});
        window.__cdmcp_locked__ = false;
        return JSON.stringify({{removed: removed}});
    }})()
    """
    raw = session.evaluate(js)
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
    return {"removed": []}
