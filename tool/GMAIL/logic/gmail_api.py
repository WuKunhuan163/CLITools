"""Gmail REST API client with OAuth2 token management.

Replaces DOM-based scraping with official Gmail API calls.
CDMCP is only used for the OAuth consent flow; all data operations
go through https://gmail.googleapis.com/gmail/v1/.

OAuth2 flow:
  1. User runs ``GMAIL setup`` to provide client_id + client_secret
  2. User runs ``GMAIL auth`` — opens consent URL in browser, user approves
  3. Authorization code is exchanged for access + refresh tokens
  4. Tokens are stored locally and auto-refreshed as needed
"""
import json
import os
import time
import base64
import urllib.request
import urllib.parse
import urllib.error
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, Any, Optional, List

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_TOOL_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _TOOL_DIR / "data"
_CREDENTIALS_PATH = _DATA_DIR / "credentials.json"
_TOKEN_PATH = _DATA_DIR / "token.json"

GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]
REDIRECT_URI = "urn:ietf:wg:oauth:2.0:oob"


# ---------------------------------------------------------------------------
# Credential & Token I/O
# ---------------------------------------------------------------------------

def _ensure_data_dir():
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def save_credentials(client_id: str, client_secret: str):
    _ensure_data_dir()
    payload = {"client_id": client_id, "client_secret": client_secret}
    _CREDENTIALS_PATH.write_text(json.dumps(payload, indent=2))


def load_credentials() -> Optional[Dict[str, str]]:
    if not _CREDENTIALS_PATH.exists():
        return None
    try:
        return json.loads(_CREDENTIALS_PATH.read_text())
    except Exception:
        return None


def save_token(token_data: Dict[str, Any]):
    _ensure_data_dir()
    _TOKEN_PATH.write_text(json.dumps(token_data, indent=2))


def load_token() -> Optional[Dict[str, Any]]:
    if not _TOKEN_PATH.exists():
        return None
    try:
        return json.loads(_TOKEN_PATH.read_text())
    except Exception:
        return None


def has_credentials() -> bool:
    creds = load_credentials()
    return creds is not None and bool(creds.get("client_id"))


def has_token() -> bool:
    token = load_token()
    return token is not None and bool(token.get("access_token"))


# ---------------------------------------------------------------------------
# OAuth2 Flow
# ---------------------------------------------------------------------------

def get_auth_url() -> Optional[str]:
    """Build the Google OAuth2 consent URL."""
    creds = load_credentials()
    if not creds:
        return None
    params = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    })
    return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"


def exchange_code(code: str) -> Dict[str, Any]:
    """Exchange an authorization code for access + refresh tokens."""
    creds = load_credentials()
    if not creds:
        return {"ok": False, "error": "No credentials configured. Run GMAIL setup first."}

    data = urllib.parse.urlencode({
        "code": code,
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            token_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"ok": False, "error": f"Token exchange failed ({e.code}): {body}"}

    token_data["obtained_at"] = int(time.time())
    save_token(token_data)
    return {"ok": True, "token": token_data}


def refresh_access_token() -> Dict[str, Any]:
    """Refresh the access token using the stored refresh token."""
    creds = load_credentials()
    token = load_token()
    if not creds or not token or not token.get("refresh_token"):
        return {"ok": False, "error": "No refresh token available. Run GMAIL auth again."}

    data = urllib.parse.urlencode({
        "client_id": creds["client_id"],
        "client_secret": creds["client_secret"],
        "refresh_token": token["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            new_data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        return {"ok": False, "error": f"Token refresh failed ({e.code}): {body}"}

    token["access_token"] = new_data["access_token"]
    token["expires_in"] = new_data.get("expires_in", 3600)
    token["obtained_at"] = int(time.time())
    if new_data.get("refresh_token"):
        token["refresh_token"] = new_data["refresh_token"]
    save_token(token)
    return {"ok": True, "token": token}


def _get_valid_token() -> Optional[str]:
    """Return a valid access token, refreshing if expired."""
    token = load_token()
    if not token or not token.get("access_token"):
        return None

    expires_in = token.get("expires_in", 3600)
    obtained_at = token.get("obtained_at", 0)
    if time.time() > obtained_at + expires_in - 60:
        result = refresh_access_token()
        if not result.get("ok"):
            return None
        token = load_token()

    return token.get("access_token") if token else None


# ---------------------------------------------------------------------------
# Gmail API helpers
# ---------------------------------------------------------------------------

def _api_request(
    method: str,
    path: str,
    body: Optional[Dict] = None,
    params: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Make an authenticated request to the Gmail API."""
    access_token = _get_valid_token()
    if not access_token:
        return {"ok": False, "error": "Not authenticated. Run GMAIL auth first."}

    url = f"{GMAIL_API_BASE}{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    data = json.dumps(body).encode() if body else None
    if method == "GET":
        data = None

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            result = json.loads(raw) if raw else {}
            result["ok"] = True
            return result
    except urllib.error.HTTPError as e:
        body_text = e.read().decode() if e.fp else ""
        if e.code == 401:
            refreshed = refresh_access_token()
            if refreshed.get("ok"):
                return _api_request(method, path, body, params)
            return {"ok": False, "error": "Authentication expired. Run GMAIL auth again."}
        return {"ok": False, "error": f"API error ({e.code}): {body_text}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _api_get(path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
    return _api_request("GET", path, params=params)


def _api_post(path: str, body: Optional[Dict] = None) -> Dict[str, Any]:
    return _api_request("POST", path, body=body)


def _api_delete(path: str) -> Dict[str, Any]:
    return _api_request("DELETE", path)


# ---------------------------------------------------------------------------
# Gmail API operations
# ---------------------------------------------------------------------------

def get_profile() -> Dict[str, Any]:
    """Get the authenticated user's Gmail profile (email, messages total, etc.)."""
    return _api_get("/users/me/profile")


def list_labels() -> Dict[str, Any]:
    """List all Gmail labels for the authenticated user."""
    result = _api_get("/users/me/labels")
    if not result.get("ok"):
        return result
    labels = result.get("labels", [])
    return {"ok": True, "count": len(labels), "labels": labels}


def get_label(label_id: str) -> Dict[str, Any]:
    """Get details for a specific label (including message/thread counts)."""
    return _api_get(f"/users/me/labels/{urllib.parse.quote(label_id)}")


def list_messages(
    query: str = "",
    label_ids: Optional[List[str]] = None,
    max_results: int = 20,
    page_token: str = "",
) -> Dict[str, Any]:
    """List message IDs matching the query. Use get_message() for full content."""
    params: Dict[str, Any] = {"maxResults": max_results}
    if query:
        params["q"] = query
    if label_ids:
        params["labelIds"] = ",".join(label_ids)
    if page_token:
        params["pageToken"] = page_token
    return _api_get("/users/me/messages", params)


def get_message(msg_id: str, fmt: str = "metadata") -> Dict[str, Any]:
    """Get a single message. fmt: 'full', 'metadata', 'minimal', 'raw'."""
    return _api_get(
        f"/users/me/messages/{urllib.parse.quote(msg_id)}",
        params={"format": fmt},
    )


def _extract_header(msg: Dict, name: str) -> str:
    """Extract a header value from a message's payload.headers."""
    headers = msg.get("payload", {}).get("headers", [])
    for h in headers:
        if h.get("name", "").lower() == name.lower():
            return h.get("value", "")
    return ""


def get_inbox(limit: int = 20) -> Dict[str, Any]:
    """Get inbox emails with from/subject/date/snippet/unread/starred."""
    result = list_messages(label_ids=["INBOX"], max_results=limit)
    if not result.get("ok"):
        return result

    messages = result.get("messages", [])
    emails = []
    for msg_stub in messages:
        msg = get_message(msg_stub["id"], fmt="metadata")
        if not msg.get("ok"):
            continue
        label_ids = msg.get("labelIds", [])
        emails.append({
            "id": msg.get("id", ""),
            "threadId": msg.get("threadId", ""),
            "from": _extract_header(msg, "From"),
            "subject": _extract_header(msg, "Subject"),
            "date": _extract_header(msg, "Date"),
            "snippet": msg.get("snippet", ""),
            "unread": "UNREAD" in label_ids,
            "starred": "STARRED" in label_ids,
        })

    return {"ok": True, "count": len(emails), "emails": emails}


def search_emails(query: str, limit: int = 10) -> Dict[str, Any]:
    """Search emails and return summaries."""
    result = list_messages(query=query, max_results=limit)
    if not result.get("ok"):
        return result

    messages = result.get("messages", [])
    emails = []
    for msg_stub in messages:
        msg = get_message(msg_stub["id"], fmt="metadata")
        if not msg.get("ok"):
            continue
        emails.append({
            "id": msg.get("id", ""),
            "from": _extract_header(msg, "From"),
            "subject": _extract_header(msg, "Subject"),
            "date": _extract_header(msg, "Date"),
            "snippet": msg.get("snippet", ""),
        })

    return {"ok": True, "query": query, "count": len(emails), "emails": emails}


def get_message_body(msg_id: str) -> Dict[str, Any]:
    """Get the full body text of a message."""
    msg = get_message(msg_id, fmt="full")
    if not msg.get("ok"):
        return msg

    def _decode_part(part: Dict) -> str:
        data = part.get("body", {}).get("data", "")
        if data:
            padded = data + "=" * (4 - len(data) % 4)
            try:
                return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
            except Exception:
                return ""
        return ""

    def _extract_text(payload: Dict) -> str:
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            return _decode_part(payload)
        if "parts" in payload:
            for part in payload["parts"]:
                text = _extract_text(part)
                if text:
                    return text
        return _decode_part(payload)

    body = _extract_text(msg.get("payload", {}))
    return {
        "ok": True,
        "id": msg_id,
        "from": _extract_header(msg, "From"),
        "subject": _extract_header(msg, "Subject"),
        "date": _extract_header(msg, "Date"),
        "body": body,
    }


def trash_message(msg_id: str) -> Dict[str, Any]:
    """Move a message to Trash."""
    return _api_post(f"/users/me/messages/{urllib.parse.quote(msg_id)}/trash")


def untrash_message(msg_id: str) -> Dict[str, Any]:
    """Remove a message from Trash."""
    return _api_post(f"/users/me/messages/{urllib.parse.quote(msg_id)}/untrash")


def mark_as_read(msg_id: str) -> Dict[str, Any]:
    """Mark a message as read (remove UNREAD label)."""
    return _api_post(
        f"/users/me/messages/{urllib.parse.quote(msg_id)}/modify",
        body={"removeLabelIds": ["UNREAD"]},
    )


def mark_as_unread(msg_id: str) -> Dict[str, Any]:
    """Mark a message as unread (add UNREAD label)."""
    return _api_post(
        f"/users/me/messages/{urllib.parse.quote(msg_id)}/modify",
        body={"addLabelIds": ["UNREAD"]},
    )


def star_message(msg_id: str) -> Dict[str, Any]:
    """Star a message."""
    return _api_post(
        f"/users/me/messages/{urllib.parse.quote(msg_id)}/modify",
        body={"addLabelIds": ["STARRED"]},
    )


def unstar_message(msg_id: str) -> Dict[str, Any]:
    """Unstar a message."""
    return _api_post(
        f"/users/me/messages/{urllib.parse.quote(msg_id)}/modify",
        body={"removeLabelIds": ["STARRED"]},
    )


def send_email(to: str, subject: str = "", body: str = "",
               cc: str = "", bcc: str = "") -> Dict[str, Any]:
    """Compose and send an email via the Gmail API."""
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    if cc:
        msg["cc"] = cc
    if bcc:
        msg["bcc"] = bcc

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    return _api_post("/users/me/messages/send", body={"raw": raw})


def list_threads(
    query: str = "",
    max_results: int = 20,
    page_token: str = "",
) -> Dict[str, Any]:
    """List threads matching the query."""
    params: Dict[str, Any] = {"maxResults": max_results}
    if query:
        params["q"] = query
    if page_token:
        params["pageToken"] = page_token
    return _api_get("/users/me/threads", params)


def get_thread(thread_id: str) -> Dict[str, Any]:
    """Get a full thread with all messages."""
    return _api_get(f"/users/me/threads/{urllib.parse.quote(thread_id)}")
