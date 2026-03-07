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
    label.textContent = 'Locked by CDMCP, Click to unlock';
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


def set_lock_passthrough(session: CDPSession, passthrough: bool = True) -> bool:
    """Toggle pointer-events on the lock shade for agent interactions.

    When passthrough=True, the shade remains visible but CDP clicks pass through
    to underlying elements. The unlock label stays clickable.
    """
    pe_value = "none" if passthrough else "auto"
    js = f"""
    (function() {{
        var shade = document.getElementById('{CDMCP_LOCK_ID}');
        if (!shade) return 'not_found';
        shade.style.pointerEvents = '{pe_value}';
        var label = shade.querySelector('div');
        if (label) label.style.pointerEvents = 'auto';
        return 'ok';
    }})()
    """
    return session.evaluate(js) == "ok"


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


# ---------------------------------------------------------------------------
# Tab pinning and favicon
# ---------------------------------------------------------------------------

def inject_favicon(session: CDPSession, svg_color: str = "#1a73e8",
                   letter: str = "C") -> bool:
    """Set a custom favicon on the tab using an inline SVG data URI."""
    js = f"""
    (function() {{
        var existing = document.querySelector('link[rel="icon"][data-cdmcp]');
        if (existing) existing.remove();
        var link = document.createElement('link');
        link.rel = 'icon';
        link.setAttribute('data-cdmcp', '1');
        link.href = "data:image/svg+xml," + encodeURIComponent(
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>" +
            "<rect width='100' height='100' rx='20' fill='{svg_color}'/>" +
            "<text y='72' x='50' text-anchor='middle' font-size='60' " +
            "font-family='system-ui' font-weight='bold' fill='white'>{letter}</text></svg>"
        );
        document.head.appendChild(link);
        return 'favicon_set';
    }})()
    """
    return session.evaluate(js) == "favicon_set"


def activate_tab(tab_id: str, port: int = CDP_PORT) -> bool:
    """Bring a tab to the foreground using browser-level CDP."""
    import urllib.request
    try:
        ver_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(ver_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return False
        bs = CDPSession(browser_ws, timeout=10)
        bs.send_and_recv("Target.activateTarget", {"targetId": tab_id})
        bs.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Tab pinning via extension chrome.tabs API
# ---------------------------------------------------------------------------

def _get_browser_ws(port: int = CDP_PORT) -> Optional[str]:
    """Get the browser-level WebSocket URL."""
    import urllib.request
    try:
        ver_url = f"http://localhost:{port}/json/version"
        with urllib.request.urlopen(ver_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return data.get("webSocketDebuggerUrl")
    except Exception:
        return None


def _find_extension_with_tabs(port: int = CDP_PORT) -> Optional[Dict[str, str]]:
    """Find a service worker extension target that has chrome.tabs access.

    Returns dict with 'targetId' and 'url' if found, else None.
    Caches the result for the session.
    """
    import websocket as _ws
    browser_ws = _get_browser_ws(port)
    if not browser_ws:
        return None

    ws = _ws.create_connection(browser_ws, timeout=10)
    msg_id = [1]

    def send(method, params=None, sid=None):
        msg = {"id": msg_id[0], "method": method}
        if params:
            msg["params"] = params
        if sid:
            msg["sessionId"] = sid
        ws.send(json.dumps(msg))
        msg_id[0] += 1
        deadline = time.time() + 8
        while time.time() < deadline:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id[0] - 1:
                return resp
        return None

    try:
        result = send("Target.getTargets")
        targets = result.get("result", {}).get("targetInfos", [])

        for t in targets:
            if t.get("type") != "service_worker":
                continue
            if not t.get("url", "").startswith("chrome-extension://"):
                continue

            tid = t["targetId"]
            attach = send("Target.attachToTarget", {"targetId": tid, "flatten": True})
            sid = (attach or {}).get("result", {}).get("sessionId")
            if not sid:
                continue

            probe = send("Runtime.evaluate", {
                "expression": "(async()=>{try{await chrome.tabs.query({});return 'ok';}catch(e){return 'no';}})()",
                "returnByValue": True,
                "awaitPromise": True,
            }, sid=sid)
            val = (probe or {}).get("result", {}).get("result", {}).get("value")

            send("Target.detachFromTarget", {"sessionId": sid})

            if val == "ok":
                return {"targetId": tid, "url": t.get("url", "")}
    except Exception:
        pass
    finally:
        try:
            ws.close()
        except Exception:
            pass
    return None


_CACHED_EXT_TARGET: Optional[Dict[str, str]] = None


def pin_tab(chrome_tab_id: int, pinned: bool = True, port: int = CDP_PORT) -> bool:
    """Pin or unpin a tab using an extension's chrome.tabs API.

    Args:
        chrome_tab_id: The Chrome-internal tab ID (integer from chrome.tabs).
        pinned: True to pin, False to unpin.
        port: CDP debug port.

    Returns True on success.
    """
    global _CACHED_EXT_TARGET
    import websocket as _ws

    if _CACHED_EXT_TARGET is None:
        _CACHED_EXT_TARGET = _find_extension_with_tabs(port)
    ext = _CACHED_EXT_TARGET
    if not ext:
        return False

    browser_ws = _get_browser_ws(port)
    if not browser_ws:
        return False

    ws = _ws.create_connection(browser_ws, timeout=10)
    msg_id = [1]

    def send(method, params=None, sid=None):
        msg = {"id": msg_id[0], "method": method}
        if params:
            msg["params"] = params
        if sid:
            msg["sessionId"] = sid
        ws.send(json.dumps(msg))
        msg_id[0] += 1
        deadline = time.time() + 8
        while time.time() < deadline:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id[0] - 1:
                return resp
        return None

    try:
        attach = send("Target.attachToTarget", {"targetId": ext["targetId"], "flatten": True})
        sid = (attach or {}).get("result", {}).get("sessionId")
        if not sid:
            _CACHED_EXT_TARGET = None
            return False

        pin_str = "true" if pinned else "false"
        expr = (
            f"(async()=>{{try{{const t=await chrome.tabs.update({chrome_tab_id},"
            f"{{pinned:{pin_str}}});return JSON.stringify({{ok:true,pinned:t.pinned}});}}"
            f"catch(e){{return JSON.stringify({{ok:false,error:e.message}});}}}})() "
        )
        result = send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        }, sid=sid)

        send("Target.detachFromTarget", {"sessionId": sid})

        val = (result or {}).get("result", {}).get("result", {}).get("value", "{}")
        parsed = json.loads(val)
        return parsed.get("ok", False)
    except Exception:
        return False
    finally:
        try:
            ws.close()
        except Exception:
            pass


def get_chrome_tab_id(cdp_target_id: str, port: int = CDP_PORT) -> Optional[int]:
    """Map a CDP target ID to a Chrome-internal tab ID (used by chrome.tabs API).

    Returns the integer tab ID, or None if not found.
    """
    global _CACHED_EXT_TARGET
    import websocket as _ws

    if _CACHED_EXT_TARGET is None:
        _CACHED_EXT_TARGET = _find_extension_with_tabs(port)
    ext = _CACHED_EXT_TARGET
    if not ext:
        return None

    browser_ws = _get_browser_ws(port)
    if not browser_ws:
        return None

    ws = _ws.create_connection(browser_ws, timeout=10)
    msg_id = [1]

    def send(method, params=None, sid=None):
        msg = {"id": msg_id[0], "method": method}
        if params:
            msg["params"] = params
        if sid:
            msg["sessionId"] = sid
        ws.send(json.dumps(msg))
        msg_id[0] += 1
        deadline = time.time() + 8
        while time.time() < deadline:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id[0] - 1:
                return resp
        return None

    try:
        attach = send("Target.attachToTarget", {"targetId": ext["targetId"], "flatten": True})
        sid = (attach or {}).get("result", {}).get("sessionId")
        if not sid:
            return None

        all_tabs = list_tabs(port=port)
        target_tab = None
        for tab in all_tabs:
            if tab.get("id") == cdp_target_id:
                target_tab = tab
                break
        if not target_tab:
            return None

        target_url = target_tab.get("url", "")
        target_title = target_tab.get("title", "")

        expr = (
            "(async()=>{const tabs=await chrome.tabs.query({});"
            "return JSON.stringify(tabs.map(t=>({id:t.id,url:(t.url||''),title:(t.title||'')})));})()"
        )
        result = send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        }, sid=sid)

        send("Target.detachFromTarget", {"sessionId": sid})

        val = (result or {}).get("result", {}).get("result", {}).get("value", "[]")
        chrome_tabs = json.loads(val)

        for ct in chrome_tabs:
            if ct.get("url") == target_url and ct.get("title") == target_title:
                return ct["id"]

        for ct in chrome_tabs:
            if ct.get("url") == target_url:
                return ct["id"]

        return None
    except Exception:
        return None
    finally:
        try:
            ws.close()
        except Exception:
            pass


def pin_tab_by_target_id(cdp_target_id: str, pinned: bool = True,
                          port: int = CDP_PORT) -> bool:
    """Pin/unpin a tab by CDP target ID in a single WS session (fast path).

    Combines tab ID resolution and pinning into one WebSocket connection
    to minimize latency.
    """
    global _CACHED_EXT_TARGET
    import websocket as _ws

    if _CACHED_EXT_TARGET is None:
        _CACHED_EXT_TARGET = _find_extension_with_tabs(port)
    ext = _CACHED_EXT_TARGET
    if not ext:
        return False

    browser_ws = _get_browser_ws(port)
    if not browser_ws:
        return False

    target_tab = None
    for tab in list_tabs(port=port):
        if tab.get("id") == cdp_target_id:
            target_tab = tab
            break
    if not target_tab:
        return False

    target_url = target_tab.get("url", "")
    target_title = target_tab.get("title", "")
    pin_str = "true" if pinned else "false"

    ws = _ws.create_connection(browser_ws, timeout=10)
    msg_id = [1]

    def send(method, params=None, sid=None):
        msg = {"id": msg_id[0], "method": method}
        if params:
            msg["params"] = params
        if sid:
            msg["sessionId"] = sid
        ws.send(json.dumps(msg))
        msg_id[0] += 1
        deadline = time.time() + 8
        while time.time() < deadline:
            resp = json.loads(ws.recv())
            if resp.get("id") == msg_id[0] - 1:
                return resp
        return None

    try:
        attach = send("Target.attachToTarget", {"targetId": ext["targetId"], "flatten": True})
        sid = (attach or {}).get("result", {}).get("sessionId")
        if not sid:
            _CACHED_EXT_TARGET = None
            return False

        # Resolve + pin in one shot
        expr = (
            f"(async()=>{{try{{"
            f"const tabs=await chrome.tabs.query({{}});"
            f"const t=tabs.find(t=>t.url==={json.dumps(target_url)});"
            f"if(!t)return JSON.stringify({{ok:false,error:'tab not found'}});"
            f"const u=await chrome.tabs.update(t.id,{{pinned:{pin_str}}});"
            f"return JSON.stringify({{ok:true,pinned:u.pinned,id:u.id}});"
            f"}}catch(e){{return JSON.stringify({{ok:false,error:e.message}});}}}})() "
        )
        result = send("Runtime.evaluate", {
            "expression": expr,
            "returnByValue": True,
            "awaitPromise": True,
        }, sid=sid)

        send("Target.detachFromTarget", {"sessionId": sid})

        val = (result or {}).get("result", {}).get("result", {}).get("value", "{}")
        parsed = json.loads(val)
        return parsed.get("ok", False)
    except Exception:
        return False
    finally:
        try:
            ws.close()
        except Exception:
            pass
