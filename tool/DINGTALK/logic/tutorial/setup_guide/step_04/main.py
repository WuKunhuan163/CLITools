"""Step 4: Validate credentials and verify phone identity."""
import tkinter as tk
import json
from pathlib import Path
from interface.gui import get_label_style
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_FILE = _TOOL_DIR / "data" / "config.json"


def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def _validate_credentials(app_key: str, app_secret: str) -> dict:
    import urllib.request
    try:
        body = json.dumps({"appKey": app_key, "appSecret": app_secret}).encode()
        req = urllib.request.Request(
            "https://api.dingtalk.com/v1.0/oauth2/accessToken",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            token = data.get("accessToken")
            if token:
                return {"ok": True, "token": token}
            return {"ok": False, "error": data.get("message", str(data))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _verify_phone(token: str, phone: str) -> dict:
    """Try to verify the phone number via contact API (old token needed)."""
    import urllib.request
    try:
        req = urllib.request.Request(
            f"https://oapi.dingtalk.com/topapi/v2/user/getbymobile?access_token={token}",
            data=json.dumps({"mobile": phone}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("errcode", -1) == 0:
            userid = data.get("result", {}).get("userid", "")
            return {"ok": True, "userid": userid}
        if "60011" in str(data.get("sub_code", "")):
            return {"ok": False, "error": "permission_missing"}
        return {"ok": False, "error": data.get("errmsg", "")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _get_old_token(app_key: str, app_secret: str) -> str:
    import urllib.request
    body = json.dumps({"appkey": app_key, "appsecret": app_secret})
    req = urllib.request.Request(
        f"https://oapi.dingtalk.com/gettoken?appkey={app_key}&appsecret={app_secret}",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return data.get("access_token", "")


def build_step(frame, win):
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _(
        "tutorial_step4_title",
        "Step 4: Validate & Complete"
    ), is_title=True)

    status_block = win.add_block(frame, pady=(10, 5))

    cfg = {}
    app_key = ""
    app_secret = ""
    active_phone = ""
    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text())
            active_phone = cfg.get("active_phone", "")
            acct = cfg.get("accounts", {}).get(active_phone, {})
            app_key = acct.get("app_key", "") or cfg.get("app_key", "")
            app_secret = acct.get("app_secret", "") or cfg.get("app_secret", "")
        except Exception:
            pass

    if not app_key or not app_secret:
        win.setup_label(status_block, _(
            "tutorial_step4_missing",
            "No credentials found in configuration.\n\n"
            "Please go back to Step 2 and save your Client ID and Client Secret."
        ))
        win.set_step_validated(False)
        return

    info_text = f"Checking credentials for: {app_key}"
    if active_phone and active_phone != "default":
        info_text += f"\nPhone: {active_phone}"
    info_block = win.add_block(frame, pady=(5, 5))
    win.setup_label(info_block, info_text)

    result_block = win.add_block(frame, pady=(10, 10))
    result = _validate_credentials(app_key, app_secret)

    if result.get("ok"):
        lines = [
            "Credentials validated successfully!",
            f"Token preview: {result['token'][:20]}...",
            "",
        ]

        if active_phone and active_phone != "default":
            try:
                old_token = _get_old_token(app_key, app_secret)
                if old_token:
                    phone_result = _verify_phone(old_token, active_phone)
                    if phone_result.get("ok"):
                        userid = phone_result.get("userid", "?")
                        lines.append(f"Phone verified: {active_phone} -> userId: {userid}")
                        acct = cfg.get("accounts", {}).get(active_phone, {})
                        if acct:
                            acct["operator_id"] = userid
                            cfg["accounts"][active_phone] = acct
                            _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
                        lines.append("")
                    elif phone_result.get("error") == "permission_missing":
                        lines.append(f"Phone: {active_phone} (contact permission not yet enabled)")
                        lines.append("Run: DINGTALK --tutorial contacts  to enable")
                        lines.append("")
                    else:
                        lines.append(f"Phone verification: {phone_result.get('error', '?')}")
                        lines.append("")
            except Exception:
                lines.append(f"Phone: {active_phone} (verification skipped)")
                lines.append("")

        lines.extend([
            "Configuration saved and ready to use.",
            "",
            "Available commands:",
            "  DINGTALK status              Check status",
            "  DINGTALK accounts            List accounts",
            "  DINGTALK switch <phone>      Switch account",
            "  DINGTALK contact <phone>     Look up a contact",
            "  DINGTALK send \"msg\" --phone <phone>",
            "",
            "Enable more permissions with:",
            "  DINGTALK --tutorial contacts",
            "  DINGTALK --tutorial messaging",
            "  DINGTALK --tutorial todo",
            "  DINGTALK --tutorial calendar",
        ])

        result_label = tk.Label(
            result_block,
            text="\n".join(lines),
            font=get_label_style(),
            fg="#228B22",
            bg=result_block.cget("bg"),
            justify="left",
            wraplength=600,
        )
        result_label.pack(anchor="w", padx=10)
        win.set_step_validated(True)
    else:
        error_msg = result.get("error", "Unknown error")
        result_label = tk.Label(
            result_block,
            text=f"Validation failed:\n{error_msg}\n\n"
                 "Please check your credentials and try again.\n"
                 "Go back to Step 2 to update them.",
            font=get_label_style(),
            fg="#cc3333",
            bg=result_block.cget("bg"),
            justify="left",
            wraplength=600,
        )
        result_label.pack(anchor="w", padx=10)
        win.set_step_validated(False)
