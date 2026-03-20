"""Common prerequisite checks for DingTalk tutorials."""
import json
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_CONFIG_FILE = _TOOL_DIR / "data" / "config.json"


def check_setup_complete() -> dict:
    """Check if setup tutorial has been completed (credentials saved).
    Returns {"ok": bool, "app_key": str, "error": str}.
    """
    if not _CONFIG_FILE.exists():
        return {"ok": False, "error": "No configuration found. Run: DINGTALK --tutorial setup"}

    try:
        cfg = json.loads(_CONFIG_FILE.read_text())
    except Exception:
        return {"ok": False, "error": "Configuration file is corrupted."}

    if cfg.get("accounts"):
        active_phone = cfg.get("active_phone", "")
        accounts = cfg.get("accounts", {})
        acct = accounts.get(active_phone) or (next(iter(accounts.values())) if accounts else {})
        app_key = acct.get("app_key", "")
        app_secret = acct.get("app_secret", "")
    else:
        app_key = cfg.get("app_key", "")
        app_secret = cfg.get("app_secret", "")

    if not app_key or not app_secret:
        return {"ok": False, "error": "Credentials not configured. Run: DINGTALK --tutorial setup"}

    return {"ok": True, "app_key": app_key}


def validate_token() -> dict:
    """Attempt to get an access token to verify credentials are still valid."""
    import urllib.request
    check = check_setup_complete()
    if not check["ok"]:
        return check

    cfg = json.loads(_CONFIG_FILE.read_text())
    if cfg.get("accounts"):
        active_phone = cfg.get("active_phone", "")
        accounts = cfg.get("accounts", {})
        acct = accounts.get(active_phone) or (next(iter(accounts.values())) if accounts else {})
    else:
        acct = cfg
    try:
        body = json.dumps({
            "appKey": acct["app_key"],
            "appSecret": acct["app_secret"]
        }).encode()
        req = urllib.request.Request(
            "https://api.dingtalk.com/v1.0/oauth2/accessToken",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            if data.get("accessToken"):
                return {"ok": True, "token": data["accessToken"]}
            return {"ok": False, "error": data.get("message", "Token request failed")}
    except Exception as e:
        return {"ok": False, "error": str(e)}
