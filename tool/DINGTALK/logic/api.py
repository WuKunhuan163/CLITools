"""DingTalk Open Platform API client.

Uses the official DingTalk Open Platform REST API (api.dingtalk.com + oapi.dingtalk.com).
No browser automation or CDMCP - fully compliant with ToS.

Two token types:
  - New API token: POST api.dingtalk.com/v1.0/oauth2/accessToken
    Used with header: x-acs-dingtalk-access-token
  - Old API token: GET oapi.dingtalk.com/gettoken
    Used with query param: ?access_token=

Both expire after 2 hours. Cached in config with expiry timestamps.
"""
import json
import time
import hashlib
import hmac
import base64
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    import requests
except ImportError:
    requests = None

_TOOL_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = _TOOL_DIR / "data"
_CONFIG_FILE = _DATA_DIR / "config.json"

NEW_API_BASE = "https://api.dingtalk.com"
OLD_API_BASE = "https://oapi.dingtalk.com"


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_config(cfg: dict):
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def _require_requests():
    if requests is None:
        raise RuntimeError("requests library required. Run: pip install requests")


def _get_new_token(app_key: str, app_secret: str) -> str:
    """Get new-style access token (api.dingtalk.com)."""
    _require_requests()
    cfg = _load_config()
    cached = cfg.get("new_token")
    expiry = cfg.get("new_token_expiry", 0)
    if cached and time.time() < expiry:
        return cached

    resp = requests.post(
        f"{NEW_API_BASE}/v1.0/oauth2/accessToken",
        json={"appKey": app_key, "appSecret": app_secret},
        timeout=10,
    )
    data = resp.json()
    token = data.get("accessToken")
    if not token:
        raise RuntimeError(f"Failed to get new token: {data}")

    cfg["new_token"] = token
    cfg["new_token_expiry"] = time.time() + 7000
    _save_config(cfg)
    return token


def _get_old_token(app_key: str, app_secret: str) -> str:
    """Get old-style access token (oapi.dingtalk.com)."""
    _require_requests()
    cfg = _load_config()
    cached = cfg.get("old_token")
    expiry = cfg.get("old_token_expiry", 0)
    if cached and time.time() < expiry:
        return cached

    resp = requests.get(
        f"{OLD_API_BASE}/gettoken",
        params={"appkey": app_key, "appsecret": app_secret},
        timeout=10,
    )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"Failed to get old token: {data}")

    cfg["old_token"] = token
    cfg["old_token_expiry"] = time.time() + 7000
    _save_config(cfg)
    return token


def _get_credentials() -> tuple:
    """Return (app_key, app_secret) from config."""
    cfg = _load_config()
    key = cfg.get("app_key") or cfg.get("DINGTALK_APP_KEY")
    secret = cfg.get("app_secret") or cfg.get("DINGTALK_APP_SECRET")
    if not key or not secret:
        raise RuntimeError(
            "DingTalk credentials not configured. "
            "Run: DINGTALK config app_key <KEY> && DINGTALK config app_secret <SECRET>"
        )
    return key, secret


def _new_api_headers(token: str) -> dict:
    return {
        "Content-Type": "application/json",
        "x-acs-dingtalk-access-token": token,
    }


# ── Contact API ──────────────────────────────────────────────


def get_user_by_mobile(mobile: str) -> Dict[str, Any]:
    """Look up userId by phone number. Returns {"ok": true, "userid": "..."}."""
    _require_requests()
    key, secret = _get_credentials()
    token = _get_old_token(key, secret)

    resp = requests.post(
        f"{OLD_API_BASE}/topapi/v2/user/getbymobile",
        params={"access_token": token},
        json={"mobile": mobile},
        timeout=10,
    )
    data = resp.json()
    if data.get("errcode", -1) != 0:
        return {"ok": False, "error": data.get("errmsg", str(data))}

    result = data.get("result", {})
    return {"ok": True, "userid": result.get("userid")}


def get_user_detail(userid: str) -> Dict[str, Any]:
    """Get full user profile by userId."""
    _require_requests()
    key, secret = _get_credentials()
    token = _get_old_token(key, secret)

    resp = requests.post(
        f"{OLD_API_BASE}/topapi/v2/user/get",
        params={"access_token": token},
        json={"userid": userid, "language": "zh_CN"},
        timeout=10,
    )
    data = resp.json()
    if data.get("errcode", -1) != 0:
        return {"ok": False, "error": data.get("errmsg", str(data))}

    return {"ok": True, "user": data.get("result", {})}


def search_users(query: str, limit: int = 20) -> Dict[str, Any]:
    """Search users by keyword. Returns list of userIds."""
    _require_requests()
    key, secret = _get_credentials()
    token = _get_new_token(key, secret)

    resp = requests.post(
        f"{NEW_API_BASE}/v1.0/contact/users/search",
        headers=_new_api_headers(token),
        json={"queryWord": query, "offset": 0, "size": min(limit, 20)},
        timeout=10,
    )
    data = resp.json()
    return {
        "ok": True,
        "userids": data.get("list", []),
        "total": data.get("totalCount", 0),
    }


# ── Message API ──────────────────────────────────────────────


def send_robot_message(
    user_ids: List[str],
    content: str,
    msg_type: str = "text",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Send robot 1:1 message to users by userId.

    msg_type: 'text' or 'markdown'
    For markdown, title is required.
    """
    _require_requests()
    key, secret = _get_credentials()
    token = _get_new_token(key, secret)

    if msg_type == "markdown":
        msg_key = "sampleMarkdown"
        msg_param = json.dumps({"title": title or "Notification", "text": content})
    else:
        msg_key = "sampleText"
        msg_param = json.dumps({"content": content})

    resp = requests.post(
        f"{NEW_API_BASE}/v1.0/robot/oToMessages/batchSend",
        headers=_new_api_headers(token),
        json={
            "robotCode": key,
            "userIds": user_ids[:20],
            "msgKey": msg_key,
            "msgParam": msg_param,
        },
        timeout=15,
    )
    data = resp.json()
    pqk = data.get("processQueryKey")
    invalid = data.get("invalidStaffIdList", [])
    if invalid:
        return {"ok": False, "error": f"Invalid user IDs: {invalid}", "data": data}
    return {"ok": True, "processQueryKey": pqk, "data": data}


def send_robot_group_message(
    conversation_id: str,
    content: str,
    msg_type: str = "text",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Send robot message to a group by openConversationId."""
    _require_requests()
    key, secret = _get_credentials()
    token = _get_new_token(key, secret)

    if msg_type == "markdown":
        msg_key = "sampleMarkdown"
        msg_param = json.dumps({"title": title or "Notification", "text": content})
    else:
        msg_key = "sampleText"
        msg_param = json.dumps({"content": content})

    resp = requests.post(
        f"{NEW_API_BASE}/v1.0/robot/groupMessages/send",
        headers=_new_api_headers(token),
        json={
            "robotCode": key,
            "openConversationId": conversation_id,
            "msgKey": msg_key,
            "msgParam": msg_param,
        },
        timeout=15,
    )
    return {"ok": True, "data": resp.json()}


def send_webhook_message(
    webhook_url: str,
    content: str,
    msg_type: str = "text",
    title: Optional[str] = None,
    secret: Optional[str] = None,
    at_mobiles: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Send message via webhook robot."""
    _require_requests()

    url = webhook_url
    if secret:
        timestamp = str(int(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code).decode("utf-8"))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"

    if msg_type == "markdown":
        body = {
            "msgtype": "markdown",
            "markdown": {"title": title or "Notification", "text": content},
        }
    else:
        body = {"msgtype": "text", "text": {"content": content}}

    if at_mobiles:
        body["at"] = {"atMobiles": at_mobiles, "isAtAll": False}

    resp = requests.post(url, json=body, timeout=10)
    data = resp.json()
    if data.get("errcode", 0) != 0:
        return {"ok": False, "error": data.get("errmsg", str(data))}
    return {"ok": True}


def send_work_notification(
    user_ids: Optional[List[str]] = None,
    content: str = "",
    msg_type: str = "text",
    title: Optional[str] = None,
    to_all: bool = False,
) -> Dict[str, Any]:
    """Send work notification (appears in the work notification channel)."""
    _require_requests()
    key, secret = _get_credentials()
    cfg = _load_config()
    agent_id = cfg.get("agent_id") or cfg.get("DINGTALK_AGENT_ID")
    if not agent_id:
        return {"ok": False, "error": "agent_id not configured. Run: DINGTALK config agent_id <ID>"}

    token = _get_old_token(key, secret)

    if msg_type == "markdown":
        msg = {"msgtype": "markdown", "markdown": {"title": title or "Notification", "text": content}}
    else:
        msg = {"msgtype": "text", "text": {"content": content}}

    body: Dict[str, Any] = {"agent_id": agent_id, "msg": msg}
    if to_all:
        body["to_all_user"] = True
    elif user_ids:
        body["userid_list"] = ",".join(user_ids[:100])
    else:
        return {"ok": False, "error": "Must specify user_ids or to_all=True"}

    resp = requests.post(
        f"{OLD_API_BASE}/topapi/message/corpconversation/asyncsend_v2",
        params={"access_token": token},
        json=body,
        timeout=15,
    )
    data = resp.json()
    if data.get("errcode", -1) != 0:
        return {"ok": False, "error": data.get("errmsg", str(data))}
    return {"ok": True, "task_id": data.get("task_id")}


# ── Todo API ─────────────────────────────────────────────────


def create_todo(
    subject: str,
    description: str = "",
    due_time: Optional[int] = None,
    executor_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Create a DingTalk todo task."""
    _require_requests()
    key, secret = _get_credentials()
    cfg = _load_config()
    operator_id = cfg.get("operator_id")
    if not operator_id:
        return {"ok": False, "error": "operator_id not configured. Run: DINGTALK config operator_id <USERID>"}

    token = _get_new_token(key, secret)

    body: Dict[str, Any] = {
        "subject": subject,
        "description": description,
        "creatorId": operator_id,
    }
    if due_time:
        body["dueTime"] = due_time
    if executor_ids:
        body["executorIds"] = executor_ids

    resp = requests.post(
        f"{NEW_API_BASE}/v1.0/todo/users/{operator_id}/tasks",
        headers=_new_api_headers(token),
        json=body,
        timeout=10,
    )
    data = resp.json()
    if "id" in data:
        return {"ok": True, "task_id": data["id"], "data": data}
    return {"ok": False, "error": str(data)}


# ── Convenience: send by phone number ────────────────────────


def send_message_to_phone(
    phone: str,
    content: str,
    msg_type: str = "text",
    title: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve phone number to userId, then send robot 1:1 message."""
    phone = phone.lstrip("+").lstrip("86")
    lookup = get_user_by_mobile(phone)
    if not lookup.get("ok"):
        return {"ok": False, "error": f"Phone lookup failed: {lookup.get('error')}"}

    userid = lookup["userid"]
    return send_robot_message([userid], content, msg_type, title)
