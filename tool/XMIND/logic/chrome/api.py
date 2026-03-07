"""XMind operations via CDMCP (Chrome DevTools MCP).

Uses the authenticated ``app.xmind.com`` session via CDP (port 9222).
The web app stores user/team data in cookies and localStorage.
Mind map listings are read from the DOM of the home page.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

XMIND_URL_PATTERN = "xmind"


def find_xmind_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the XMind tab in Chrome."""
    return find_tab(XMIND_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_xmind_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check XMind authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "XMind tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var isLogin = url.includes("/login") || url.includes("/signin");
                var isHome = url.includes("/home") || url.includes("/recents");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    isLogin: isLogin,
                    authenticated: isHome && !isLogin
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get XMind page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "XMind tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title,
                    section: window.location.pathname.split('/').filter(Boolean).pop() || 'home'
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_maps(port: int = CDP_PORT) -> Dict[str, Any]:
    """List mind maps visible on the current page (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "XMind tab not found"}
    try:
        r = session.evaluate("""
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
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_sidebar(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read sidebar navigation items (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "XMind tab not found"}
    try:
        r = session.evaluate("""
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
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
