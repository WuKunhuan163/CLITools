"""Gmail operations via the official Gmail REST API.

Previously used DOM scraping via CDMCP; now migrated to the Gmail API
(https://gmail.googleapis.com/gmail/v1/) for ToS compliance.

CDMCP is retained **only** for:
  - Checking if a Gmail tab is open (get_auth_state)
  - Opening the OAuth consent URL during ``GMAIL auth``

All data read/write goes through :mod:`tool.GMAIL.logic.gmail_api`.
"""
import json
from typing import Dict, Any, Optional

from interface.chrome import (
    CDPSession, CDP_PORT,
    is_chrome_cdp_available,
    find_tab,
)

from tool.GMAIL.logic.gmail_api import (
    has_credentials,
    has_token,
    get_profile,
    get_inbox as _api_get_inbox,
    list_labels as _api_list_labels,
    get_label as _api_get_label,
    search_emails as _api_search_emails,
    trash_message as _api_trash_message,
    send_email as _api_send_email,
    get_message as _api_get_message,
    get_message_body as _api_get_message_body,
    mark_as_read as _api_mark_as_read,
    mark_as_unread as _api_mark_as_unread,
    star_message as _api_star_message,
    unstar_message as _api_unstar_message,
    list_messages as _api_list_messages,
)

GMAIL_URL_PATTERN = "mail.google.com"


# ---------------------------------------------------------------------------
# CDMCP helpers (auth state only)
# ---------------------------------------------------------------------------

def find_gmail_tab(port: int = CDP_PORT) -> Optional[Dict[str, Any]]:
    """Find the Gmail tab in Chrome (for auth flow)."""
    return find_tab(GMAIL_URL_PATTERN, port=port, tab_type="page")


def get_auth_state(port: int = CDP_PORT) -> Dict[str, Any]:
    """Check authentication state using both API token and browser tab.

    Returns a dict with:
      - ``authenticated``: True if a valid Gmail API token exists
      - ``credentials_configured``: True if OAuth client_id is set up
      - ``gmail_tab_open``: True if a Gmail tab is open in Chrome
      - ``email``, ``unreadCount``: from Gmail API profile (if authenticated)
    """
    state: Dict[str, Any] = {
        "ok": True,
        "credentials_configured": has_credentials(),
        "token_stored": has_token(),
        "authenticated": False,
        "gmail_tab_open": False,
        "email": None,
        "unreadCount": None,
    }

    if is_chrome_cdp_available(port):
        tab = find_gmail_tab(port)
        state["gmail_tab_open"] = tab is not None

    if has_token():
        profile = get_profile()
        if profile.get("ok"):
            state["authenticated"] = True
            state["email"] = profile.get("emailAddress")
            total = profile.get("messagesTotal")
            state["messagesTotal"] = total

    return state


def get_page_info(port: int = CDP_PORT) -> Dict[str, Any]:
    """Get Gmail browser tab info (URL, title, section). Uses CDMCP read-only."""
    if not is_chrome_cdp_available(port):
        return {"ok": False, "error": "Chrome CDP not available"}

    tab = find_gmail_tab(port)
    if not tab or not tab.get("webSocketDebuggerUrl"):
        return {"ok": False, "error": "Gmail tab not found"}

    try:
        session = CDPSession(tab["webSocketDebuggerUrl"])
    except Exception:
        return {"ok": False, "error": "Cannot connect to Gmail tab"}

    try:
        r = session.evaluate("""
            (function() {
                var url = window.location.href;
                var hash = url.split("#")[1] || "";
                var section = hash.split("/")[0] || "inbox";
                return JSON.stringify({
                    ok: true,
                    url: url,
                    title: document.title,
                    section: section
                });
            })()
        """)
        return json.loads(r) if r else {"ok": False, "error": "No response"}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Gmail API wrappers (public interface — drop-in replacements)
# ---------------------------------------------------------------------------

def get_inbox(limit: int = 20, port: int = CDP_PORT) -> Dict[str, Any]:
    """Read inbox emails via the Gmail API."""
    return _api_get_inbox(limit=limit)


def get_labels(port: int = CDP_PORT) -> Dict[str, Any]:
    """List Gmail labels via the API."""
    result = _api_list_labels()
    if not result.get("ok"):
        return result

    labels = []
    for lb in result.get("labels", []):
        label_id = lb.get("id", "")
        detail = _api_get_label(label_id)
        count = None
        if detail.get("ok"):
            total = detail.get("messagesTotal")
            unread = detail.get("messagesUnread")
            count = str(unread) if unread else (str(total) if total else None)
        labels.append({
            "name": lb.get("name", label_id),
            "id": label_id,
            "type": lb.get("type", "user"),
            "count": count,
        })

    return {"ok": True, "count": len(labels), "labels": labels}


def search_emails(query: str, limit: int = 10, port: int = CDP_PORT) -> Dict[str, Any]:
    """Search emails via the Gmail API."""
    return _api_search_emails(query, limit=limit)


def delete_email(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Move an email to Trash via the Gmail API.

    Now takes a message ID instead of a DOM row index.
    """
    result = _api_trash_message(msg_id)
    if result.get("ok"):
        result["deleted"] = True
    return result


def send_email(to: str, subject: str = "", body: str = "",
               cc: str = "", bcc: str = "",
               port: int = CDP_PORT) -> Dict[str, Any]:
    """Send an email via the Gmail API."""
    result = _api_send_email(to, subject=subject, body=body, cc=cc, bcc=bcc)
    if result.get("ok"):
        result["sent"] = True
    return result


def get_message(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get message metadata."""
    return _api_get_message(msg_id, fmt="metadata")


def get_message_body(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Get full message body text."""
    return _api_get_message_body(msg_id)


def mark_read(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Mark a message as read."""
    return _api_mark_as_read(msg_id)


def mark_unread(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Mark a message as unread."""
    return _api_mark_as_unread(msg_id)


def star(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Star a message."""
    return _api_star_message(msg_id)


def unstar(msg_id: str, port: int = CDP_PORT) -> Dict[str, Any]:
    """Unstar a message."""
    return _api_unstar_message(msg_id)


def list_messages(query: str = "", label_ids=None, max_results: int = 20,
                  page_token: str = "", port: int = CDP_PORT) -> Dict[str, Any]:
    """List message IDs matching the query."""
    return _api_list_messages(
        query=query, label_ids=label_ids,
        max_results=max_results, page_token=page_token,
    )
