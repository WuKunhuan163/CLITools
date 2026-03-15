"""PayPal operations via Chrome DevTools Protocol.

Uses the authenticated ``paypal.com`` session for auth state detection only.
DOM scraping functions are disabled due to PayPal ToS violations.

PayPal explicitly prohibits "robots, spiders, scraping or other technology
to access, query, or use www.PayPal.com." Data operations should use the
PayPal REST API (developer.paypal.com) with OAuth credentials.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
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


# TODO: Migrate to PayPal REST API (developer.paypal.com) with OAuth credentials.
# DOM scraping violates PayPal ToS. See for_agent.md ## ToS Compliance.

def get_account_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read account info. DISABLED: violates PayPal ToS (DOM scraping)."""
    return {"ok": False, "error": "Disabled: PayPal ToS prohibits DOM scraping. Use PayPal REST API instead."}


def get_recent_activity(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read recent transactions. DISABLED: violates PayPal ToS (DOM scraping)."""
    return {"ok": False, "error": "Disabled: PayPal ToS prohibits DOM scraping. Use PayPal REST API instead."}
