"""WhatsApp Web operations via CDMCP (Chrome DevTools MCP).

Uses the ``web.whatsapp.com`` session for auth state detection only.
DOM scraping and message sending functions are disabled due to WhatsApp
ToS violations.

WhatsApp explicitly prohibits "unofficial clients, auto-messaging,
auto-dialing, or automation." Data operations should use the WhatsApp
Business Cloud API (developers.facebook.com/docs/whatsapp/).
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    find_tab,
)

WHATSAPP_URL_PATTERN = "web.whatsapp.com"


def find_whatsapp_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the WhatsApp Web tab in Chrome."""
    return find_tab(WHATSAPP_URL_PATTERN, port=port, tab_type="page")


def _get_session(port: int = CDP_PORT) -> Optional[CDPSession]:
    tab = find_whatsapp_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return None
    try:
        return CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return None


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check WhatsApp Web authentication / link state."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "authenticated": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var chatList = document.querySelector(
                    "[data-testid='chat-list'], [aria-label='Chat list'], #pane-side"
                );
                var searchBox = document.querySelector("[data-testid='chat-list-search']");
                var body = (document.body ? document.body.innerText : "").substring(0, 200);
                var needsQr = body.includes("Scan") || body.includes("Link with phone");
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    authenticated: !!chatList || !!searchBox,
                    needsQrScan: needsQr && !chatList
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "authenticated": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "authenticated": False, "error": str(e)}
    finally:
        session.close()


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get WhatsApp Web page info."""
    session = _get_session(port)
    if not session:
        return {"ok": False, "error": "WhatsApp tab not found"}
    try:
        r = session.evaluate("""
            (function() {
                return JSON.stringify({
                    ok: true,
                    url: window.location.href,
                    title: document.title
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


# TODO: Migrate to WhatsApp Business Cloud API (developers.facebook.com/docs/whatsapp/).
# DOM scraping and UI automation violate WhatsApp ToS. See for_agent.md ## ToS Compliance.

_TOS_ERR = "Disabled: WhatsApp ToS prohibits automated access. Use WhatsApp Business Cloud API instead."


def get_chats(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read visible chat list. DISABLED: violates WhatsApp ToS (DOM scraping)."""
    return {"ok": False, "error": _TOS_ERR}


def get_profile(port: int = CDP_PORT) -> Dict[str, Any]:
    """Read profile info. DISABLED: violates WhatsApp ToS."""
    return {"ok": False, "error": _TOS_ERR}


def search_contact(query: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search contacts. DISABLED: violates WhatsApp ToS (UI automation)."""
    return {"ok": False, "error": _TOS_ERR}


def send_to_contact(name: str, message: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Send message by contact name. DISABLED: violates WhatsApp ToS."""
    return {"ok": False, "error": _TOS_ERR}


def send_message(phone: str, message: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Send message by phone number. DISABLED: violates WhatsApp ToS."""
    return {"ok": False, "error": _TOS_ERR}
