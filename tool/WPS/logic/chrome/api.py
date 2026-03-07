"""WPS Office / KDocs operations via Chrome DevTools Protocol.

Uses the ``kdocs.cn`` or ``wps.com`` session.  When authenticated,
the tool can list recent documents and read user info.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

WPS_URL_PATTERNS = ["kdocs", "wps.cn", "wps.com"]


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
    """Read user info from WPS page (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WPS tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var avatar = document.querySelector(
                        "[class*=avatar] img, [class*=Avatar] img, [class*=user] img"
                    );
                    var nameEl = document.querySelector(
                        "[class*=userName], [class*=user-name], [class*=nickname]"
                    );
                    var ls = {};
                    try {
                        for (var i = 0; i < localStorage.length; i++) {
                            var k = localStorage.key(i);
                            if (k && (k.includes("user") || k.includes("token") || k.includes("nick"))) {
                                var v = localStorage.getItem(k);
                                if (v && v.length < 200) ls[k] = v;
                            }
                        }
                    } catch(e) {}
                    return JSON.stringify({
                        ok: true,
                        data: {
                            name: nameEl ? nameEl.textContent.trim() : null,
                            avatarUrl: avatar ? avatar.src : null,
                            localStorage: ls
                        }
                    });
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


def get_recent_docs(port: int = CDP_PORT) -> Dict[str, Any]:
    """List recent documents from KDocs/WPS page DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WPS tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var items = document.querySelectorAll(
                        "[class*=file-item], [class*=FileItem], [class*=doc-item], " +
                        "[class*=recent-item], tr[class*=file], [data-testid*=file]"
                    );
                    var docs = Array.from(items).slice(0, 20).map(function(el) {
                        var name = el.querySelector(
                            "[class*=file-name], [class*=fileName], [class*=title]"
                        );
                        var time = el.querySelector(
                            "[class*=time], [class*=date], [class*=modify]"
                        );
                        return {
                            name: name ? name.textContent.trim().substring(0, 80) : el.textContent.trim().substring(0, 80),
                            time: time ? time.textContent.trim() : ""
                        };
                    });
                    return JSON.stringify({ok: true, count: docs.length, docs: docs});
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
