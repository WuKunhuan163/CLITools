"""Linear operations via Chrome DevTools Protocol.

Uses the authenticated ``linear.app`` session.  User and organization
data is read from ``localStorage`` (``ApplicationStore``) since Linear's
GraphQL API (``client-api.linear.app``) requires token auth that is not
sent via cross-origin cookies.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
)

LINEAR_URL_PATTERN = "linear.app"


def find_linear_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Linear app tab in Chrome."""
    return find_tab(LINEAR_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_linear_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Linear authentication state from cookies and localStorage."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "Linear tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var loggedIn = document.cookie.split(";").map(c => c.trim())
                    .find(c => c.startsWith("loggedIn="));
                var isLoggedIn = loggedIn ? loggedIn.split("=")[1] === "1" : false;

                var appStore = {};
                try { appStore = JSON.parse(localStorage.getItem("ApplicationStore") || "{}"); }
                catch(_) {}

                var accountId = appStore.currentUserAccountId || null;
                var accounts = appStore.userAccounts || {};
                var account = accountId ? accounts[accountId] : null;

                return JSON.stringify({
                    ok: true,
                    authenticated: isLoggedIn,
                    accountId: accountId,
                    email: account ? account.email : null,
                    hasOrganizations: (account && account.users && account.users.length > 0) || false,
                    availableOrgs: appStore.availableOrganizations || []
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_user_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Linear user info from localStorage."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Linear tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                try {
                    var appStore = JSON.parse(localStorage.getItem("ApplicationStore") || "{}");
                    var accountId = appStore.currentUserAccountId;
                    var accounts = appStore.userAccounts || {};
                    var account = accountId ? accounts[accountId] : null;

                    if (!account) return JSON.stringify({ok: false, error: "No account data"});

                    return JSON.stringify({
                        ok: true,
                        data: {
                            accountId: accountId,
                            email: account.email,
                            service: account.service,
                            organizations: (account.users || []).map(u => ({
                                id: u.id, name: u.name, organizationId: u.organizationId
                            })),
                            availableOrganizations: (appStore.availableOrganizations || []).map(o => ({
                                id: o.id, name: o.name, urlKey: o.urlKey
                            }))
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


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get current Linear page state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Linear tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title,
                    pathname: window.location.pathname
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()
