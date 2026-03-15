"""Sentry operations via Chrome DevTools Protocol.

Uses the authenticated ``sentry.io`` session.  Sentry provides a
same-origin REST API at ``/api/0/`` that works with session cookies,
so authenticated API calls can be made via CDP ``fetch()``.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
    fetch_api,
)

SENTRY_URL_PATTERN = "sentry.io"


def find_sentry_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Sentry tab in Chrome."""
    return find_tab(SENTRY_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_sentry_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def _sentry_api(endpoint: str, method: str = "GET",
                port: int = CDP_PORT, timeout: int = 15) -> Dict[str, Any]:
    """Call a Sentry API endpoint via CDP fetch (same-origin)."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Sentry tab not found"}
    try:
        result = fetch_api(session, endpoint, method=method, timeout=timeout)
        if result is not None:
            return {"ok": True, "data": result}
        return {"ok": False, "error": "No response from API"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Sentry authentication state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "Sentry tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var isLogin = url.includes("/auth/login") || url.includes("/welcome");
                var isSetup = url.includes("/setup") || url.includes("extensions/google");
                var title = document.title;
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    isLogin: isLogin,
                    isSetup: isSetup,
                    authenticated: !isLogin && !isSetup && !url.includes("/welcome")
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the current Sentry page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Sentry tab not found"}
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


def get_organizations(port: int = CDP_PORT) -> Dict[str, Any]:
    """List Sentry organizations (requires auth)."""
    return _sentry_api("/api/0/organizations/", port=port)


def get_projects(org_slug: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """List projects in an organization (requires auth)."""
    return _sentry_api(f"/api/0/organizations/{org_slug}/projects/", port=port)


def get_issues(org_slug: str, project_slug: str = None,
               port: int = CDP_PORT) -> Dict[str, Any]:
    """List recent issues (requires auth)."""
    ep = f"/api/0/organizations/{org_slug}/issues/"
    if project_slug:
        ep += f"?project={project_slug}"
    return _sentry_api(ep, port=port)
