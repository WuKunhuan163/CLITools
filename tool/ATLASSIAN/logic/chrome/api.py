"""Atlassian API operations via Chrome DevTools Protocol.

Uses the authenticated ``home.atlassian.com`` session to make API calls
through the gateway API at ``/gateway/api/``.
"""
import json
from typing import Dict, Any, Optional

from logic.chrome.session import (
    CDPSession, CDP_PORT,
    find_tab,
)

ATLASSIAN_URL_PATTERN = "atlassian.com"


def find_atlassian_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Atlassian Home tab in Chrome."""
    return find_tab(ATLASSIAN_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_atlassian_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def _atlassian_api(endpoint: str, method: str = "GET", body: dict = None,
                   port: int = CDP_PORT, timeout: int = 15) -> Dict[str, Any]:
    """Call an Atlassian API endpoint via CDP fetch."""
    session = _get_session(port)
    if not session:
        return {"error": "Atlassian tab not found in Chrome"}
    try:
        body_part = ""
        if body:
            body_part = f", body: JSON.stringify({json.dumps(body)})"
        js = f"""
            (async function() {{
                try {{
                    var resp = await fetch("{endpoint}", {{
                        method: "{method}",
                        credentials: "include",
                        headers: {{"Accept": "application/json", "Content-Type": "application/json"}}
                        {body_part}
                    }});
                    var text = await resp.text();
                    try {{
                        return JSON.stringify({{ok: resp.ok, status: resp.status, data: JSON.parse(text)}});
                    }} catch(_) {{
                        return JSON.stringify({{ok: resp.ok, status: resp.status, data: text.substring(0, 500)}});
                    }}
                }} catch(e) {{
                    return JSON.stringify({{ok: false, status: 0, data: e.toString()}});
                }}
            }})()
        """
        raw = session.evaluate(js, timeout=timeout)
        if raw:
            return json.loads(raw)
        return {"ok": False, "status": 0, "data": "No response"}
    except Exception as e:
        return {"ok": False, "status": 0, "data": str(e)}
    finally:
        session.close()


def get_me(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the authenticated Atlassian user profile."""
    return _atlassian_api("/gateway/api/me", port=port)


def get_notifications(max_count: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get recent notifications."""
    return _atlassian_api(
        f"/gateway/api/notification-log/api/2/notifications?direct=true&max={max_count}",
        port=port,
    )


def get_user_preferences(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get user profile preferences (locale, timezone)."""
    result = get_me(port)
    if result.get("ok") and isinstance(result.get("data"), dict):
        data = result["data"]
        return {
            "ok": True,
            "data": {
                "name": data.get("name"),
                "email": data.get("email"),
                "locale": data.get("locale"),
                "account_type": data.get("account_type"),
                "account_status": data.get("account_status"),
                "nickname": data.get("nickname"),
            }
        }
    return result
