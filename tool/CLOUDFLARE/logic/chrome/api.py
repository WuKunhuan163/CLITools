"""Cloudflare API operations via Chrome DevTools Protocol.

Uses the authenticated ``dash.cloudflare.com`` session to make API calls
through the same-origin proxy at ``/api/v4/``.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
)

CF_URL_PATTERN = "dash.cloudflare.com"


def find_cloudflare_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Cloudflare dashboard tab in Chrome."""
    return find_tab(CF_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_cloudflare_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def _get_account_id(session: CDPSession) -> Optional[str]:
    """Extract the Cloudflare account ID from the current page URL."""
    path = session.evaluate("window.location.pathname")
    if path:
        parts = path.strip("/").split("/")
        if parts and len(parts[0]) == 32:
            return parts[0]
    return None


def _cf_api(endpoint: str, method: str = "GET", body: str = None,
            port: int = CDP_PORT, timeout: int = 15) -> Dict[str, Any]:
    """Call a Cloudflare API endpoint via CDP fetch on the dashboard tab."""
    session = _get_session(port)
    if not session:
        return {"success": False, "error": "Cloudflare dashboard tab not found"}
    try:
        body_part = ""
        if body:
            body_part = f", body: {json.dumps(body)}"
        js = f"""
            (async function() {{
                try {{
                    var resp = await fetch(window.location.origin + "{endpoint}", {{
                        method: "{method}",
                        credentials: "include",
                        headers: {{"Accept": "application/json", "Content-Type": "application/json"}}
                        {body_part}
                    }});
                    var data = await resp.json();
                    return JSON.stringify(data);
                }} catch(e) {{
                    return JSON.stringify({{success: false, errors: [{{message: e.toString()}}]}});
                }}
            }})()
        """
        raw = session.evaluate(js, timeout=timeout)
        if raw:
            return json.loads(raw)
        return {"success": False, "errors": [{"message": "No response"}]}
    except Exception as e:
        return {"success": False, "errors": [{"message": str(e)}]}
    finally:
        session.close()


def get_user(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the authenticated Cloudflare user info."""
    return _cf_api("/api/v4/user", port=port)


def get_account(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the Cloudflare account info (requires account ID from URL)."""
    session = _get_session(port)
    if not session:
        return {"success": False, "errors": [{"message": "Dashboard tab not found"}]}
    try:
        acct_id = _get_account_id(session)
        if not acct_id:
            return {"success": False, "errors": [{"message": "Cannot determine account ID from URL"}]}
    finally:
        session.close()
    return _cf_api(f"/api/v4/accounts/{acct_id}", port=port)


def list_zones(per_page: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """List DNS zones in the account."""
    return _cf_api(f"/api/v4/zones?per_page={per_page}", port=port)


def get_zone(zone_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get details for a specific zone."""
    return _cf_api(f"/api/v4/zones/{zone_id}", port=port)


def list_dns_records(zone_id: str, per_page: int = 50,
                     port: int = CDP_PORT) -> Dict[str, Any]:
    """List DNS records for a zone."""
    return _cf_api(f"/api/v4/zones/{zone_id}/dns_records?per_page={per_page}", port=port)


def list_workers(port: int = CDP_PORT) -> Dict[str, Any]:
    """List Workers scripts in the account."""
    session = _get_session(port)
    if not session:
        return {"success": False, "errors": [{"message": "Dashboard tab not found"}]}
    try:
        acct_id = _get_account_id(session)
    finally:
        session.close()
    if not acct_id:
        return {"success": False, "errors": [{"message": "Cannot determine account ID"}]}
    return _cf_api(f"/api/v4/accounts/{acct_id}/workers/scripts", port=port)


def list_pages_projects(port: int = CDP_PORT) -> Dict[str, Any]:
    """List Cloudflare Pages projects."""
    session = _get_session(port)
    if not session:
        return {"success": False, "errors": [{"message": "Dashboard tab not found"}]}
    try:
        acct_id = _get_account_id(session)
    finally:
        session.close()
    if not acct_id:
        return {"success": False, "errors": [{"message": "Cannot determine account ID"}]}
    return _cf_api(f"/api/v4/accounts/{acct_id}/pages/projects", port=port)


def list_kv_namespaces(port: int = CDP_PORT) -> Dict[str, Any]:
    """List Workers KV namespaces."""
    session = _get_session(port)
    if not session:
        return {"success": False, "errors": [{"message": "Dashboard tab not found"}]}
    try:
        acct_id = _get_account_id(session)
    finally:
        session.close()
    if not acct_id:
        return {"success": False, "errors": [{"message": "Cannot determine account ID"}]}
    return _cf_api(f"/api/v4/accounts/{acct_id}/storage/kv/namespaces", port=port)
