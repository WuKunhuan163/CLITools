"""WPS Office / KDocs operations via CDMCP (Chrome DevTools MCP).

Uses the ``kdocs.cn`` or ``wps.com`` session via CDP (port 9222).
Auth state and basic page info are read from URL/title.
DOM scraping functions (get_user_info, get_recent_docs) are disabled
due to ToS concerns. Use the KDocs Developer Platform API instead.

# TODO: Migrate to KDocs Developer Platform API for document operations.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

WPS_URL_PATTERNS = ["kdocs", "wps.cn", "wps.com"]

# TODO: Migrate to KDocs Developer Platform API for user info and documents.
_TOS_ERR = "Disabled: DOM scraping may violate WPS/KDocs ToS. Use KDocs Developer Platform API instead."


def find_wps_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the WPS/KDocs tab in Chrome."""
    for pattern in WPS_URL_PATTERNS:
        tab = find_tab(pattern, port=port, tab_type="page")
        if tab:
            return tab
    return None


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_wps_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check WPS authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "WPS tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var isLogin = url.includes("account.wps") || url.includes("/login") ||
                              url.includes("/signin") || title.toLowerCase().includes("log in");
                var isDocs = url.includes("kdocs.cn/latest") || url.includes("kdocs.cn/recent") ||
                             url.includes("/drive") || url.includes("docs.wps.com");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    isLogin: isLogin,
                    authenticated: isDocs && !isLogin
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get WPS/KDocs page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WPS tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title,
                    heading: (document.querySelector("h1, h2") || {}).textContent || ""
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_user_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get user info. DISABLED: violates WPS/KDocs ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def get_recent_docs(port: int = CDP_PORT) -> Dict[str, Any]:
    """List recent docs. DISABLED: violates WPS/KDocs ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}
