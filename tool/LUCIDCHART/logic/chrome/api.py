"""Lucidchart operations via CDMCP (Chrome DevTools MCP).

Uses standard CDMCP interfaces (via cdmcp_loader) for:
  - Session management (boot_tool_session / require_tab)
  - Visual overlays (badge, lock, focus, favicon)
  - MCP interaction effects (mcp_click, mcp_type, mcp_navigate)

All tab operations go through CDMCP session.require_tab() to ensure tabs
open in the dedicated session window.

Operations:
  - Session: boot / status / recover
  - Navigation: home, documents, templates, editor
  - Editor: shapes, text, connections, selection, alignment
  - Document: page info, layers, export
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from interface.chrome import CDPSession, CDP_PORT, capture_screenshot
from interface.cdmcp import (
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_interact,
)

from tool.LUCIDCHART.logic.chrome.state_machine import (
    LucidState, get_machine,
)

LUCID_URL_PATTERN = "lucid.app"
LUCID_HOME = "https://lucid.app/documents"

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_DATA_DIR = _TOOL_DIR / "data"


def _overlay():
    return load_cdmcp_overlay()


def _sessions():
    return load_cdmcp_sessions()


def _interact():
    return load_cdmcp_interact()


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

_session = None
_session_name = "lucidchart"


def _get_or_create_session(port: int = CDP_PORT):
    global _session
    if _session is not None:
        try:
            cdp = _session.get_cdp()
            if cdp:
                return _session
        except Exception:
            pass
        _session = None
    sm = _sessions()
    existing = sm.get_session(_session_name)
    if existing:
        try:
            cdp = existing.get_cdp()
            if cdp:
                _session = existing
                return existing
        except Exception:
            pass
        sm.close_session(_session_name)
    return None


def boot_session(port: int = CDP_PORT) -> Dict[str, Any]:
    """Boot Lucidchart in a dedicated CDMCP session window."""
    global _session
    machine = get_machine(_session_name)

    if machine.state not in (LucidState.UNINITIALIZED, LucidState.ERROR):
        existing = _get_or_create_session(port)
        if existing:
            return {"ok": True, "action": "already_booted", **machine.to_dict()}

    if machine.state == LucidState.ERROR:
        machine.transition(LucidState.RECOVERING)
        if not machine.can_recover():
            machine.reset()
        machine.transition(LucidState.UNINITIALIZED)

    machine.transition(LucidState.BOOTING, {"url": LUCID_HOME})

    sm = _sessions()
    boot_result = sm.boot_tool_session(_session_name, timeout_sec=86400, port=port)
    if not boot_result.get("ok"):
        machine.transition(LucidState.ERROR, {"error": boot_result.get("error", "Boot failed")})
        return {"ok": False, "error": boot_result.get("error"), **machine.to_dict()}

    _session = boot_result.get("session")

    tab_info = _session.require_tab(
        "lucidchart", url_pattern="lucid.app",
        open_url=LUCID_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        ov = _overlay()
        cdp = CDPSession(tab_info["ws"])
        ov.inject_favicon(cdp, svg_color="#f96b13", letter="L")
        ov.inject_badge(cdp, text="Lucidchart MCP", color="#f96b13")
        ov.inject_focus(cdp, color="#f96b13")

    machine.transition(LucidState.IDLE)
    machine.set_url(LUCID_HOME)
    return {"ok": True, "action": "booted", **machine.to_dict()}


def _ensure_session(port: int = CDP_PORT, prefer_editor: bool = True) -> Optional[CDPSession]:
    global _session
    session = _get_or_create_session(port)
    if not session:
        result = boot_session(port)
        if not result.get("ok"):
            return None
        session = _get_or_create_session(port)
    if not session:
        return None

    session.touch()

    if prefer_editor:
        import urllib.request
        try:
            tabs = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json").read())
            for t in tabs:
                turl = t.get("url", "")
                if "/lucidchart/" in turl and "/edit" in turl and t.get("webSocketDebuggerUrl"):
                    cdp = CDPSession(t["webSocketDebuggerUrl"])
                    try:
                        ov = _overlay()
                        has_badge = cdp.evaluate(
                            f"!!document.getElementById('{ov.CDMCP_BADGE_ID}')")
                        if not has_badge:
                            ov.inject_favicon(cdp, svg_color="#f96b13", letter="L")
                            ov.inject_badge(cdp, text="Lucidchart MCP", color="#f96b13")
                            ov.inject_focus(cdp, color="#f96b13")
                    except Exception:
                        pass
                    return cdp
        except Exception:
            pass

    tab_info = session.require_tab(
        "lucidchart", url_pattern="lucid.app",
        open_url=LUCID_HOME, auto_open=True, wait_sec=10,
    )
    if tab_info and tab_info.get("ws"):
        cdp = CDPSession(tab_info["ws"])
        try:
            ov = _overlay()
            has_badge = cdp.evaluate(
                f"!!document.getElementById('{ov.CDMCP_BADGE_ID}')")
            if not has_badge:
                ov.inject_favicon(cdp, svg_color="#f96b13", letter="L")
                ov.inject_badge(cdp, text="Lucidchart MCP", color="#f96b13")
                ov.inject_focus(cdp, color="#f96b13")
        except Exception:
            pass
        return cdp
    return None


def _recover(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    if not machine.can_recover():
        machine.reset()
        return boot_session(port)
    if machine.state != LucidState.RECOVERING:
        if not machine.transition(LucidState.RECOVERING):
            machine.reset()
            return boot_session(port)
    target = machine.get_recovery_target()
    result = boot_session(port)
    if not result.get("ok"):
        return result
    url = target.get("url", LUCID_HOME)
    if url != LUCID_HOME:
        cdp = _ensure_session(port)
        if cdp:
            cdp.evaluate(f"window.location.href = {json.dumps(url)}")
            time.sleep(3)
            machine.set_url(url)
    return {"ok": True, "action": "recovered", "restored_to": url, **machine.to_dict()}


def get_session_status(port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    session = _get_or_create_session(port)
    result = machine.to_dict()
    result["session_alive"] = session is not None
    from interface.chrome import is_chrome_cdp_available
    result["cdp_available"] = is_chrome_cdp_available(port)
    return result


# ---------------------------------------------------------------------------
# Auth & page info
# ---------------------------------------------------------------------------

def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var url = window.location.href;
                var isLogin = url.includes('/login') || url.includes('/signin');
                var teamHeader = document.querySelector('[class*="team-header"], [class*="account-name"]');
                var profileEl = null;
                var all = document.querySelectorAll('*');
                for(var el of all){
                    if(el.textContent.trim() === 'Personal' && el.previousElementSibling){
                        profileEl = el.previousElementSibling;
                        break;
                    }
                }
                var username = profileEl ? profileEl.textContent.trim() : '';
                if(!username && teamHeader) username = teamHeader.textContent.trim();
                var planEl = document.querySelector('[class*="plan-badge"], [class*="free-plan"]');
                var plan = '';
                var all2 = document.querySelectorAll('*');
                for(var el of all2){
                    if(el.textContent.trim().match(/^(Free|Pro|Team|Business|Enterprise) plan$/)){
                        plan = el.textContent.trim();
                        break;
                    }
                }
                return JSON.stringify({
                    ok: true,
                    authenticated: !isLogin && (!!username || url.includes('/documents')),
                    username: username,
                    plan: plan,
                    title: document.title,
                    url: url
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var url = window.location.href;
                var isEditor = url.includes('/edit') || url.includes('/lucidchart/');
                var isDocs = url.includes('/documents');
                var isTemplates = url.includes('/templates');
                var section = isEditor ? 'editor' : (isDocs ? 'documents' : (isTemplates ? 'templates' : 'other'));
                return JSON.stringify({ok: true, url: url, title: document.title, section: section});
            })()
        """)
        return json.loads(r) if r else {"ok": False}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------

_NAV_TARGETS = {
    "home": "https://lucid.app/documents",
    "documents": "https://lucid.app/documents",
    "templates": "https://lucid.app/templates",
    "recent": "https://lucid.app/documents#/recent",
    "shared": "https://lucid.app/documents#/shared-with-me",
    "trash": "https://lucid.app/documents#/trash",
}


def navigate(target: str, port: int = CDP_PORT) -> Dict[str, Any]:
    machine = get_machine(_session_name)
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        url = _NAV_TARGETS.get(target.lower(), target)
        if not url.startswith("http"):
            return {"ok": False, "error": f"Unknown target: {target}"}
        machine.transition(LucidState.NAVIGATING, {"target": target})
        interact = _interact()
        interact.mcp_navigate(session, url, tool_name="Lucidchart")
        time.sleep(3)
        actual = session.evaluate("window.location.href") or url
        machine.set_url(str(actual))
        if "/edit" in str(actual) or "/lucidchart/" in str(actual):
            machine.transition(LucidState.EDITING)
        else:
            machine.transition(LucidState.IDLE)
        return {"ok": True, "url": str(actual), "target": target}
    except Exception as e:
        machine.transition(LucidState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def create_new_document(port: int = CDP_PORT) -> Dict[str, Any]:
    """Create a new blank Lucidchart document via + New > Lucidchart > Blank document."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        machine = get_machine(_session_name)
        machine.transition(LucidState.NAVIGATING, {"action": "create_document"})
        ov = _overlay()

        current_url = session.evaluate("window.location.href") or ""
        if "documents" not in str(current_url):
            interact = _interact()
            interact.mcp_navigate(session, LUCID_HOME, tool_name="Lucidchart")
            time.sleep(3)

        ov.set_lock_passthrough(session, True)
        try:
            session.evaluate("""
                (function(){
                    var btns = document.querySelectorAll("button, [role=button]");
                    for(var b of btns){
                        if(b.textContent.trim().includes("New") && b.textContent.trim().length < 10){
                            b.click(); return;
                        }
                    }
                })()
            """)
            time.sleep(1.5)

            session.evaluate("""
                (function(){
                    var menu = document.querySelector("lucid-menu-container");
                    if(!menu) return;
                    var all = menu.querySelectorAll("*");
                    for(var el of all){
                        if(el.children.length === 0 && el.textContent.trim() === "Lucidchart"){
                            el.click(); return;
                        }
                    }
                })()
            """)
            time.sleep(1)

            session.evaluate("""
                (function(){
                    var all = document.querySelectorAll("*");
                    for(var el of all){
                        if(el.children.length === 0 && el.textContent.trim() === "Blank document"){
                            el.click(); return;
                        }
                    }
                })()
            """)
        finally:
            ov.set_lock_passthrough(session, False)

        for _ in range(10):
            time.sleep(1)
            url = str(session.evaluate("window.location.href") or "")
            if "/lucidchart/" in url or "/edit" in url:
                break

        url = str(session.evaluate("window.location.href") or "")
        machine.set_url(url)
        if "/lucidchart/" in url or "/edit" in url:
            machine.transition(LucidState.EDITING)
            ov.inject_badge(session, text="Lucidchart MCP", color="#f96b13")
            return {"ok": True, "action": "document_created", "url": url}
        else:
            machine.transition(LucidState.IDLE)
            return {"ok": True, "action": "document_created", "url": url,
                    "note": "May have opened in new tab"}
    except Exception as e:
        machine.transition(LucidState.ERROR, {"error": str(e)})
        return {"ok": False, "error": str(e)}


def open_document_by_name(name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open a document by clicking on its card in the documents view."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        machine = get_machine(_session_name)
        ov = _overlay()

        current_url = session.evaluate("window.location.href") or ""
        if "documents" not in str(current_url):
            interact = _interact()
            interact.mcp_navigate(session, LUCID_HOME, tool_name="Lucidchart")
            time.sleep(3)

        data = {}
        for attempt in range(8):
            r = session.evaluate(f"""
                (function(){{
                    var items = document.querySelectorAll("lucid-folder-entry-icon-item, lucid-folder-entry-list-item");
                    for(var el of items){{
                        if(el.textContent.includes({json.dumps(name)})){{
                            var rect = el.getBoundingClientRect();
                            return JSON.stringify({{found: true, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2)}});
                        }}
                    }}
                    return JSON.stringify({{found: false, count: items.length}});
                }})()
            """)
            data = json.loads(r) if r else {}
            if data.get("found"):
                break
            time.sleep(1)

        if not data.get("found"):
            return {"ok": False, "error": f"Document '{name}' not found"}

        x, y = data["x"], data["y"]
        ov.set_lock_passthrough(session, True)
        try:
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1
            })
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1
            })
            time.sleep(0.5)

            opened = session.evaluate("""
                (function(){
                    var openBtn = document.querySelector('button');
                    var all = document.querySelectorAll('button, a, [role="button"]');
                    for(var el of all){
                        if(el.textContent.trim() === 'Open' && el.offsetHeight > 0){
                            el.click();
                            return JSON.stringify({clicked: 'open_button'});
                        }
                    }
                    return JSON.stringify({clicked: false});
                })()
            """)
            click_data = json.loads(opened) if opened else {}
            if not click_data.get("clicked"):
                time.sleep(0.1)
                session.send_and_recv("Input.dispatchMouseEvent", {
                    "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 2
                })
                session.send_and_recv("Input.dispatchMouseEvent", {
                    "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 2
                })
        finally:
            ov.set_lock_passthrough(session, False)

        import urllib.request
        for _ in range(15):
            time.sleep(1)
            url = str(session.evaluate("window.location.href") or "")
            if "/lucidchart/" in url or "/edit" in url:
                machine.set_url(url)
                machine.transition(LucidState.EDITING)
                ov.inject_badge(session, text="Lucidchart MCP", color="#f96b13")
                return {"ok": True, "url": url, "document": name}
            tabs = json.loads(urllib.request.urlopen(
                f"http://127.0.0.1:{port}/json").read())
            for t in tabs:
                turl = t.get("url", "")
                if "/lucidchart/" in turl and "/edit" in turl:
                    new_ws = t.get("webSocketDebuggerUrl", "")
                    if new_ws:
                        new_cdp = CDPSession(new_ws)
                        ov.inject_badge(new_cdp, text="Lucidchart MCP", color="#f96b13")
                        ov.inject_favicon(new_cdp, svg_color="#f96b13", letter="L")
                        machine.set_url(turl)
                        machine.transition(LucidState.EDITING)
                        return {"ok": True, "url": turl, "document": name,
                                "note": "Opened in new tab"}

        url = str(session.evaluate("window.location.href") or "")
        return {"ok": False, "error": "Document did not open to editor", "url": url}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def open_document(doc_url: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Open a document by URL."""
    return navigate(doc_url, port)


# ---------------------------------------------------------------------------
# Screenshot
# ---------------------------------------------------------------------------

def take_screenshot(output_path: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        img = capture_screenshot(session)
        if not img:
            return {"ok": False, "error": "Screenshot failed"}
        if not output_path:
            _DATA_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(_DATA_DIR / f"screenshot_{time.strftime('%Y%m%d_%H%M%S')}.png")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(img)
        return {"ok": True, "path": output_path, "size": len(img)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Editor: Layout & Exploration
# ---------------------------------------------------------------------------

def get_editor_layout(port: int = CDP_PORT) -> Dict[str, Any]:
    """Identify the editor layout areas (toolbar, canvas, panels)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var out = {};
                out.url = window.location.href;
                out.title = document.title;
                out.is_editor = out.url.includes('/edit') || out.url.includes('/lucidchart/');

                var toolbar = document.querySelector(
                    '.toolbar, [data-testid="toolbar"], .editor-toolbar, '
                    + '#toolbar, .top-toolbar');
                out.has_toolbar = !!toolbar;

                var canvas = document.querySelector(
                    'canvas, .canvas-container, [data-testid="canvas"], '
                    + '.lucid-canvas, svg.main-canvas');
                out.has_canvas = !!canvas;
                if(canvas){
                    var r = canvas.getBoundingClientRect();
                    out.canvas_rect = {x: r.x, y: r.y, width: r.width, height: r.height};
                }

                var leftPanel = document.querySelector(
                    '.left-panel, .shapes-panel, [data-testid="shape-library"], '
                    + '.library-panel, .side-panel-left');
                out.has_shape_library = !!leftPanel;

                var rightPanel = document.querySelector(
                    '.right-panel, .properties-panel, [data-testid="properties-panel"], '
                    + '.style-panel, .side-panel-right');
                out.has_properties_panel = !!rightPanel;

                var pages = document.querySelectorAll(
                    '.page-tab, [data-testid="page-tab"], .page-list-item');
                out.page_count = pages.length;

                var allBtns = document.querySelectorAll('button');
                out.toolbar_items = [];
                for(var i=0; i<allBtns.length; i++){
                    var btn = allBtns[i];
                    var rect = btn.getBoundingClientRect();
                    if(rect.y > 40 && rect.y < 80 && rect.width > 0){
                        var text = btn.getAttribute('aria-label') ||
                                   btn.getAttribute('title') ||
                                   btn.textContent.trim();
                        if(text && text.length < 40 && text.length > 0)
                            out.toolbar_items.push(text);
                    }
                }

                var areas = [];
                if(out.has_toolbar) areas.push('Toolbar (top)');
                if(out.has_canvas) areas.push('Canvas (' + Math.round(out.canvas_rect?.width || 0) + 'x' + Math.round(out.canvas_rect?.height || 0) + ')');
                if(out.has_shape_library) areas.push('Shape library (left panel)');
                if(out.has_properties_panel) areas.push('Properties panel (right)');
                if(out.page_count > 0) areas.push('Pages (' + out.page_count + ')');
                out.areas = areas;

                return JSON.stringify(out);
            })()
        """)
        result = json.loads(r) if r else {}
        result["ok"] = True
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_documents_list(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """List documents from the documents page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        machine = get_machine(_session_name)
        current_url = session.evaluate("window.location.href") or ""
        if "documents" not in str(current_url):
            machine.transition(LucidState.NAVIGATING, {"action": "list_documents"})
            interact = _interact()
            interact.mcp_navigate(session, LUCID_HOME, tool_name="Lucidchart")
            time.sleep(3)
            machine.transition(LucidState.IDLE)

        r = session.evaluate(f"""
            (function(){{
                var items = document.querySelectorAll(
                    'lucid-folder-entry-icon-item, lucid-folder-entry-list-item, '
                    + '[data-testid="document-item"], .document-card, '
                    + '.doc-item, .file-item');
                var out = [];
                for(var i=0; i<Math.min(items.length, {limit}); i++){{
                    var el = items[i];
                    var headerEl = el.querySelector(
                        'lucid-folder-entry-icon-item-header, lucid-common-icon-item-header, '
                        + '.document-title, .title, .name');
                    var typeEl = el.querySelector('.product-label, .type-label, .subtitle');
                    var linkEl = el.querySelector('a[href]');
                    out.push({{
                        index: i,
                        title: headerEl ? headerEl.textContent.trim().substring(0, 80) : el.textContent.trim().substring(0, 80),
                        type: typeEl ? typeEl.textContent.trim() : '',
                        url: linkEl ? linkEl.getAttribute('href') || '' : ''
                    }});
                }}
                return JSON.stringify({{ok: true, count: out.length, documents: out}});
            }})()
        """)
        return json.loads(r) if r else {"ok": True, "count": 0, "documents": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Comprehensive MCP state
# ---------------------------------------------------------------------------

def get_mcp_state(port: int = CDP_PORT) -> Dict[str, Any]:
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        machine = get_machine(_session_name)
        r = session.evaluate("""
            (function(){
                var out = {};
                out.url = window.location.href;
                out.title = document.title;
                out.section = out.url.includes('/edit') || out.url.includes('/lucidchart/')
                    ? 'editor' : out.url.includes('/documents') ? 'documents'
                    : out.url.includes('/templates') ? 'templates' : 'other';

                var canvas = document.querySelector('canvas, .canvas-container, svg.main-canvas');
                out.has_canvas = !!canvas;

                var avatar = document.querySelector('.user-avatar, .avatar-image, [data-testid="user-avatar"]');
                out.authenticated = !!avatar;

                var pages = document.querySelectorAll('.page-tab, [data-testid="page-tab"]');
                out.page_count = pages.length;

                return JSON.stringify(out);
            })()
        """)
        state = json.loads(r) if r else {}
        state["machine_state"] = machine.to_dict()
        state["ok"] = True
        return state
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Navigation helpers
# ---------------------------------------------------------------------------

def go_back(port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate back to the previous page."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        session.evaluate("window.history.back()")
        time.sleep(2)
        url = session.evaluate("window.location.href") or ""
        machine = get_machine(_session_name)
        machine.set_url(str(url))
        if "/edit" in str(url) or "/lucidchart/" in str(url):
            machine.transition(LucidState.EDITING)
        else:
            machine.transition(LucidState.IDLE)
        return {"ok": True, "url": str(url)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def navigate_templates(category: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Navigate to templates gallery."""
    url = "https://lucid.app/templates"
    if category:
        url += f"?q={category}"
    return navigate(url, port)


# ---------------------------------------------------------------------------
# Editor interactions (keyboard shortcuts)
# ---------------------------------------------------------------------------

def _send_key(session: CDPSession, key: str, modifiers: int = 0):
    """Send a keyboard event to the editor."""
    key_codes = {
        'r': ('r', 'KeyR', 82),
        'o': ('o', 'KeyO', 79),
        't': ('t', 'KeyT', 84),
        'l': ('l', 'KeyL', 76),
        'a': ('a', 'KeyA', 65),
        'v': ('v', 'KeyV', 86),
        'c': ('c', 'KeyC', 67),
        'x': ('x', 'KeyX', 88),
        'z': ('z', 'KeyZ', 90),
        'g': ('g', 'KeyG', 71),
        'Delete': ('Delete', 'Delete', 46),
        'Backspace': ('Backspace', 'Backspace', 8),
        'Escape': ('Escape', 'Escape', 27),
        'Enter': ('Enter', 'Enter', 13),
        'Tab': ('Tab', 'Tab', 9),
    }
    info = key_codes.get(key, (key, f'Key{key.upper()}', ord(key.upper()) if len(key) == 1 else 0))
    k, code, kc = info
    for etype in ("keyDown", "keyUp"):
        session.send_and_recv("Input.dispatchKeyEvent", {
            "type": etype,
            "key": k,
            "code": code,
            "windowsVirtualKeyCode": kc,
            "nativeVirtualKeyCode": kc,
            "modifiers": modifiers,
        })


def _focus_canvas(session: CDPSession):
    """Click on the canvas area to ensure it has focus."""
    ov = _overlay()
    canvas = _get_canvas_center(session)
    ov.set_lock_passthrough(session, True)
    try:
        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mousePressed", "x": canvas["x"], "y": canvas["y"],
            "button": "left", "clickCount": 1
        })
        session.send_and_recv("Input.dispatchMouseEvent", {
            "type": "mouseReleased", "x": canvas["x"], "y": canvas["y"],
            "button": "left", "clickCount": 1
        })
    finally:
        ov.set_lock_passthrough(session, False)
    time.sleep(0.1)


def select_all(port: int = CDP_PORT) -> Dict[str, Any]:
    """Select all objects on the canvas (Cmd+A)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        _focus_canvas(session)
        _send_key(session, 'a', modifiers=8 if __import__('sys').platform == 'darwin' else 2)
        return {"ok": True, "action": "select_all"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def delete_selected(port: int = CDP_PORT) -> Dict[str, Any]:
    """Delete currently selected objects."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        _send_key(session, 'Backspace')
        return {"ok": True, "action": "deleted"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def copy_selected(port: int = CDP_PORT) -> Dict[str, Any]:
    """Copy selected objects (Cmd+C)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = 8 if __import__('sys').platform == 'darwin' else 2
        _send_key(session, 'c', modifiers=mod)
        return {"ok": True, "action": "copied"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def paste(port: int = CDP_PORT) -> Dict[str, Any]:
    """Paste from clipboard (Cmd+V)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = 8 if __import__('sys').platform == 'darwin' else 2
        _send_key(session, 'v', modifiers=mod)
        return {"ok": True, "action": "pasted"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def undo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Undo last action (Cmd+Z)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = 8 if __import__('sys').platform == 'darwin' else 2
        _send_key(session, 'z', modifiers=mod)
        return {"ok": True, "action": "undone"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def group_selected(port: int = CDP_PORT) -> Dict[str, Any]:
    """Group selected objects (Cmd+G)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = 8 if __import__('sys').platform == 'darwin' else 2
        _send_key(session, 'g', modifiers=mod)
        return {"ok": True, "action": "grouped"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def zoom(level: Optional[str] = None, port: int = CDP_PORT) -> Dict[str, Any]:
    """Zoom the canvas: 'in', 'out', 'fit', 'reset', or percentage."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = 8 if __import__('sys').platform == 'darwin' else 2
        if level == "in":
            _send_key(session, '+', modifiers=mod)
        elif level == "out":
            _send_key(session, '-', modifiers=mod)
        elif level == "fit":
            _send_key(session, '0', modifiers=mod | 1)
        elif level == "reset" or level == "100":
            _send_key(session, '0', modifiers=mod)
        return {"ok": True, "action": f"zoom_{level or 'current'}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def escape(port: int = CDP_PORT) -> Dict[str, Any]:
    """Press Escape to deselect or cancel current operation."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        _send_key(session, 'Escape')
        return {"ok": True, "action": "escaped"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def redo(port: int = CDP_PORT) -> Dict[str, Any]:
    """Redo last undone action (Cmd+Shift+Z)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = (8 | 1) if __import__('sys').platform == 'darwin' else (2 | 1)
        _send_key(session, 'z', modifiers=mod)
        return {"ok": True, "action": "redone"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ungroup_selected(port: int = CDP_PORT) -> Dict[str, Any]:
    """Ungroup selected objects (Cmd+Shift+G)."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        mod = (8 | 1) if __import__('sys').platform == 'darwin' else (2 | 1)
        _send_key(session, 'g', modifiers=mod)
        return {"ok": True, "action": "ungrouped"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# Editor: Shape & Object Operations
# ---------------------------------------------------------------------------

def _get_canvas_center(session: CDPSession) -> tuple:
    r = session.evaluate("""
        (function(){
            var c = document.querySelector('canvas');
            if(c){
                var r = c.getBoundingClientRect();
                return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2),
                    left: Math.round(r.x), top: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)});
            }
            return JSON.stringify({x: 500, y: 400, left: 300, top: 90, w: 800, h: 580});
        })()
    """)
    data = json.loads(r) if r else {"x": 500, "y": 400, "left": 300, "top": 90}
    return data


def add_shape(shape_name: str, x: Optional[int] = None, y: Optional[int] = None,
              port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a shape to the canvas by dragging from the shape library.

    shape_name: e.g. 'Process', 'Decision', 'Rectangle', 'Circle', 'Text', etc.
    x, y: target canvas position (absolute screen coordinates). Defaults to center.
    """
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        canvas = _get_canvas_center(session)
        target_x = x if x is not None else canvas["x"]
        target_y = y if y is not None else canvas["y"]

        shape_pos = session.evaluate(f"""
            (function(){{
                var btns = document.querySelectorAll('button');
                for(var b of btns){{
                    var label = b.getAttribute('aria-label') || b.getAttribute('title') || '';
                    if(label === {json.dumps(shape_name)}){{
                        var r = b.getBoundingClientRect();
                        if(r.width > 0){{
                            return JSON.stringify({{found: true, x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)}});
                        }}
                    }}
                }}
                return JSON.stringify({{found: false}});
            }})()
        """)
        pos = json.loads(shape_pos) if shape_pos else {}
        if not pos.get("found"):
            return {"ok": False, "error": f"Shape '{shape_name}' not found in shape library"}

        sx, sy = pos["x"], pos["y"]

        ov.set_lock_passthrough(session, True)
        try:
            steps = 15
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": sx, "y": sy, "button": "left", "clickCount": 1
            })
            for i in range(1, steps + 1):
                ix = sx + (target_x - sx) * i // steps
                iy = sy + (target_y - sy) * i // steps
                session.send_and_recv("Input.dispatchMouseEvent", {
                    "type": "mouseMoved", "x": ix, "y": iy, "button": "left"
                })
                time.sleep(0.03)
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": target_x, "y": target_y, "button": "left", "clickCount": 1
            })
        finally:
            ov.set_lock_passthrough(session, False)

        time.sleep(0.5)
        return {"ok": True, "action": "shape_added", "shape": shape_name,
                "position": {"x": target_x, "y": target_y}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_text(text: str, x: Optional[int] = None, y: Optional[int] = None,
             port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a text block to the canvas and type content."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        result = add_shape("Text", x=x, y=y, port=port)
        if not result.get("ok"):
            return result

        time.sleep(0.5)
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            for char in text:
                session.send_and_recv("Input.dispatchKeyEvent", {
                    "type": "keyDown", "text": char, "key": char,
                    "code": f"Key{char.upper()}" if char.isalpha() else "",
                })
                session.send_and_recv("Input.dispatchKeyEvent", {
                    "type": "keyUp", "key": char,
                    "code": f"Key{char.upper()}" if char.isalpha() else "",
                })
                time.sleep(0.02)
        finally:
            ov.set_lock_passthrough(session, False)

        _send_key(session, 'Escape')
        return {"ok": True, "action": "text_added", "text": text}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def click_canvas(x: int, y: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Click at a specific canvas position."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": x, "y": y, "button": "left", "clickCount": 1
            })
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": x, "y": y, "button": "left", "clickCount": 1
            })
        finally:
            ov.set_lock_passthrough(session, False)
        return {"ok": True, "action": "clicked", "position": {"x": x, "y": y}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def draw_line(x1: int, y1: int, x2: int, y2: int, port: int = CDP_PORT) -> Dict[str, Any]:
    """Draw a line from (x1,y1) to (x2,y2) using the Line tool."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        add_shape("Line", x=x1, y=y1, port=port)

        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": x1, "y": y1, "button": "left", "clickCount": 1
            })
            steps = 10
            for i in range(1, steps + 1):
                ix = x1 + (x2 - x1) * i // steps
                iy = y1 + (y2 - y1) * i // steps
                session.send_and_recv("Input.dispatchMouseEvent", {
                    "type": "mouseMoved", "x": ix, "y": iy, "button": "left"
                })
                time.sleep(0.03)
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": x2, "y": y2, "button": "left", "clickCount": 1
            })
        finally:
            ov.set_lock_passthrough(session, False)

        _send_key(session, 'Escape')
        return {"ok": True, "action": "line_drawn", "from": {"x": x1, "y": y1}, "to": {"x": x2, "y": y2}}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def set_fill_color(color: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Set fill color for selected object(s). Click the Fill color button."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            pos = session.evaluate("""
                (function(){
                    var btns = document.querySelectorAll('button');
                    for(var b of btns){
                        if((b.getAttribute('aria-label') || b.getAttribute('title')) === 'Fill color'){
                            var r = b.getBoundingClientRect();
                            return JSON.stringify({x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)});
                        }
                    }
                    return JSON.stringify({});
                })()
            """)
            pos_data = json.loads(pos) if pos else {}
            if not pos_data.get("x"):
                return {"ok": False, "error": "Fill color button not found"}

            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mousePressed", "x": pos_data["x"], "y": pos_data["y"],
                "button": "left", "clickCount": 1
            })
            session.send_and_recv("Input.dispatchMouseEvent", {
                "type": "mouseReleased", "x": pos_data["x"], "y": pos_data["y"],
                "button": "left", "clickCount": 1
            })
            time.sleep(0.5)

            session.evaluate(f"""
                (function(){{
                    var inputs = document.querySelectorAll('input[type="text"], input[aria-label*="color"], input[aria-label*="hex"]');
                    for(var inp of inputs){{
                        if(inp.offsetHeight > 0){{
                            inp.focus();
                            inp.value = '';
                            inp.value = {json.dumps(color.replace('#', ''))};
                            inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                            return JSON.stringify({{typed: true}});
                        }}
                    }}
                    return JSON.stringify({{typed: false}});
                }})()
            """)
        finally:
            ov.set_lock_passthrough(session, False)

        _send_key(session, 'Enter')
        _send_key(session, 'Escape')
        return {"ok": True, "action": "fill_color_set", "color": color}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_page_list(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the list of pages in the document."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var pages = [];
                var pageEls = document.querySelectorAll('button');
                for(var p of pageEls){
                    var label = p.getAttribute('aria-label') || p.getAttribute('title') || '';
                    if(label.startsWith('Page ') && label.length < 20){
                        pages.push(label);
                    }
                }
                var zoomEl = null;
                document.querySelectorAll('button').forEach(function(b){
                    if(b.textContent.trim().match(/^Page \\d+$/)){
                        pages.push(b.textContent.trim());
                    }
                });
                return JSON.stringify({ok: true, pages: [...new Set(pages)]});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "pages": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def add_page(port: int = CDP_PORT) -> Dict[str, Any]:
    """Add a new page to the document."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            session.evaluate("""
                (function(){
                    var btns = document.querySelectorAll('button');
                    for(var b of btns){
                        if((b.getAttribute('aria-label') || b.getAttribute('title')) === 'Add page'){
                            b.click(); return;
                        }
                    }
                })()
            """)
        finally:
            ov.set_lock_passthrough(session, False)
        time.sleep(1)
        return {"ok": True, "action": "page_added"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def get_zoom_level(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the current zoom level."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var btns = document.querySelectorAll('button');
                for(var b of btns){
                    var label = b.getAttribute('aria-label') || b.getAttribute('title') || '';
                    if(label.startsWith('Zoom level')){
                        return JSON.stringify({ok: true, zoom: label.replace('Zoom level: ', ''), text: b.textContent.trim()});
                    }
                }
                return JSON.stringify({ok: true, zoom: 'unknown'});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "zoom": "unknown"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_shape_libraries(port: int = CDP_PORT) -> Dict[str, Any]:
    """List available shape library sections."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var btns = document.querySelectorAll('button');
                var libs = [];
                for(var b of btns){
                    var label = b.getAttribute('aria-label') || b.getAttribute('title') || '';
                    if(label === 'Drag'){
                        var parent = b.closest('[class]');
                        if(parent){
                            var header = parent.querySelector('span, div');
                            if(header && header.textContent.trim().length > 0 && header.textContent.trim().length < 40){
                                libs.push(header.textContent.trim());
                            }
                        }
                    }
                }
                // Deduplicate
                return JSON.stringify({ok: true, libraries: [...new Set(libs)]});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "libraries": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def list_shapes_in_library(port: int = CDP_PORT) -> Dict[str, Any]:
    """List all available shapes from the shape library."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        r = session.evaluate("""
            (function(){
                var btns = document.querySelectorAll('button');
                var shapes = [];
                for(var b of btns){
                    var label = b.getAttribute('aria-label') || b.getAttribute('title') || '';
                    var rect = b.getBoundingClientRect();
                    if(rect.width >= 25 && rect.width <= 35 && rect.height >= 25 && rect.height <= 35
                       && rect.x > 50 && rect.x < 280 && label.length > 0){
                        shapes.push(label);
                    }
                }
                return JSON.stringify({ok: true, count: shapes.length, shapes: shapes});
            })()
        """)
        return json.loads(r) if r else {"ok": True, "shapes": []}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def toolbar_click(button_title: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Click a toolbar button by its title attribute."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            r = session.evaluate(f"""
                (function(){{
                    var btns = document.querySelectorAll('button');
                    for(var b of btns){{
                        if((b.getAttribute('aria-label') || b.getAttribute('title')) === {json.dumps(button_title)}){{
                            b.click();
                            return JSON.stringify({{clicked: true}});
                        }}
                    }}
                    return JSON.stringify({{clicked: false}});
                }})()
            """)
        finally:
            ov.set_lock_passthrough(session, False)
        data = json.loads(r) if r else {}
        if data.get("clicked"):
            return {"ok": True, "action": "toolbar_clicked", "button": button_title}
        return {"ok": False, "error": f"Button '{button_title}' not found"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def rename_document(new_name: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Rename the current document."""
    session = _ensure_session(port)
    if not session:
        return {"ok": False, "error": "No Lucidchart session"}
    try:
        ov = _overlay()
        ov.set_lock_passthrough(session, True)
        try:
            r = session.evaluate(f"""
                (function(){{
                    var titleEl = document.querySelector('[class*="document-name"], [class*="DocumentName"]');
                    if(!titleEl){{
                        var spans = document.querySelectorAll('span');
                        for(var s of spans){{
                            if(s.textContent.trim() === document.title.replace(': Lucidchart', '').trim()){{
                                titleEl = s;
                                break;
                            }}
                        }}
                    }}
                    if(titleEl){{
                        titleEl.click();
                        return JSON.stringify({{found: true}});
                    }}
                    return JSON.stringify({{found: false}});
                }})()
            """)
            found = json.loads(r) if r else {}
            if not found.get("found"):
                return {"ok": False, "error": "Document title element not found"}

            time.sleep(0.5)

            session.evaluate(f"""
                (function(){{
                    var input = document.querySelector('input[type="text"]');
                    if(!input){{
                        var inputs = document.querySelectorAll('input');
                        for(var i of inputs) if(i.offsetHeight > 0) {{ input = i; break; }}
                    }}
                    if(input){{
                        input.focus();
                        input.select();
                        input.value = {json.dumps(new_name)};
                        input.dispatchEvent(new Event('input', {{bubbles: true}}));
                        input.dispatchEvent(new Event('change', {{bubbles: true}}));
                    }}
                }})()
            """)
        finally:
            ov.set_lock_passthrough(session, False)

        _send_key(session, 'Enter')
        time.sleep(1)
        return {"ok": True, "action": "renamed", "new_name": new_name}
    except Exception as e:
        return {"ok": False, "error": str(e)}
