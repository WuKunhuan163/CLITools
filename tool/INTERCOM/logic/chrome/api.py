"""Intercom operations via Chrome DevTools Protocol.

Uses the authenticated ``app.intercom.com`` session to access Intercom's
internal API.  Falls back to DOM scraping when the user is on the sign-up
or login page.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
)

INTERCOM_URL_PATTERN = "app.intercom.com"


def find_intercom_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Intercom app tab in Chrome."""
    return find_tab(INTERCOM_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_intercom_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check Intercom authentication state."""
    session = _get_session(port)
    if not session:
        return {"authenticated": False, "error": "Intercom tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var isSignUp = url.includes("sign_up") || url.includes("sign_in");
                var cookies = document.cookie.split(";").map(c => c.trim().split("=")[0]).filter(c => c);
                var hasSession = cookies.some(c => c.includes("session") || c === "gbu9uvfhph6a0mdatwbzomssrlboczvs");
                return JSON.stringify({
                    url: url,
                    isSignUp: isSignUp,
                    hasSession: hasSession,
                    pageTitle: document.title
                });
            })()
        """)
        if r:
            data = json.loads(r)
            data["authenticated"] = data.get("hasSession") and not data.get("isSignUp")
            return data
        return {"authenticated": False, "error": "No response"}
    except Exception as e:
        return {"authenticated": False, "error": str(e)}
    finally:
        session.close()


def _intercom_api(endpoint: str, method: str = "GET", body: dict = None,
                  port: int = CDP_PORT, timeout: int = 15) -> Dict[str, Any]:
    """Call an Intercom API endpoint via CDP fetch."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Intercom tab not found"}
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


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get the current Intercom page info and visible content."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "Intercom tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var title = document.title;
                var h1 = document.querySelector("h1");
                var heading = h1 ? h1.textContent.trim() : "";
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: title,
                    heading: heading
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


def get_conversations(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """List recent conversations (requires authenticated session)."""
    return _intercom_api(f"/ember/inbox/conversations?per_page={limit}", port=port)


def get_contacts(limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """List contacts (requires authenticated session)."""
    return _intercom_api(f"/ember/contacts?per_page={limit}", port=port)
