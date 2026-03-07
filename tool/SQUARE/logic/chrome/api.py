"""Square operations via Chrome DevTools Protocol.

Uses the authenticated ``squareup.com`` session.  Square's internal
API endpoints live under the same origin so CDP ``fetch()`` works
once authenticated.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    find_tab,
)

SQUARE_URL_PATTERN = "squareup.com"


def find_square_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Square tab in Chrome."""
    return find_tab(SQUARE_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_square_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Square authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "Square tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var isLogin = url.includes("/login") || url.includes("/signin");
                var title = document.title;
                var isDashboard = url.includes("/dashboard") || url.includes("/home");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    isLogin: isLogin,
                    authenticated: isDashboard && !isLogin
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the current Square page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Square tab not found"}
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


def get_dashboard_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read dashboard summary from DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Square tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var name = document.querySelector(
                        "[data-testid='merchant-name'], [class*=merchant], [class*=business]"
                    );
                    var balance = document.querySelector("[class*=balance], [class*=Balance]");
                    var summary = document.querySelector("[class*=summary], [class*=overview]");
                    return JSON.stringify({
                        ok: true,
                        data: {
                            merchantName: name ? name.textContent.trim() : null,
                            balance: balance ? balance.textContent.trim() : null,
                            summary: summary ? summary.textContent.trim().substring(0, 200) : null
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
