"""PayPal operations via Chrome DevTools Protocol.

Uses the authenticated ``paypal.com`` session.  When the user is on
the login page the tool reports auth state; when authenticated it can
read account info and recent activity from the dashboard DOM and
internal APIs.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
    fetch_api,
)

PAYPAL_URL_PATTERN = "paypal.com"


def find_paypal_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the PayPal tab in Chrome."""
    return find_tab(PAYPAL_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_paypal_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check PayPal authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "PayPal tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var isLogin = url.includes("/signin") || url.includes("/login");
                var cookies = document.cookie.split(";").map(c => c.trim().split("=")[0]).filter(c => c);
                var hasSession = cookies.some(c =>
                    c === "LANG" || c === "login_email" || c === "X-PP-SILOVER"
                );
                var isDashboard = url.includes("/myaccount") || url.includes("/summary");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    isLogin: isLogin,
                    authenticated: isDashboard && !isLogin,
                    hasSession: hasSession
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the current PayPal page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "PayPal tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title,
                    heading: (document.querySelector("h1") || {}).textContent || ""
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_account_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read account info from the dashboard DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "PayPal tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var name = document.querySelector("[data-testid='header-name'], .headerName, [class*=userName]");
                    var balance = document.querySelector("[data-testid='balance'], [class*=balance], [class*=Balance]");
                    var email = document.querySelector("[data-testid='email'], [class*=email]");
                    return JSON.stringify({
                        ok: true,
                        data: {
                            name: name ? name.textContent.trim() : null,
                            balance: balance ? balance.textContent.trim() : null,
                            email: email ? email.textContent.trim() : null
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


def get_recent_activity(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read recent transactions from the dashboard DOM (requires auth)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "PayPal tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var rows = document.querySelectorAll(
                        "[data-testid='activity-row'], [class*=transaction], tr[class*=activity]"
                    );
                    var items = Array.from(rows).slice(0, 20).map(el => ({
                        text: el.textContent.trim().replace(/\\s+/g, " ").substring(0, 120)
                    }));
                    return JSON.stringify({ok: true, count: items.length, items: items});
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
