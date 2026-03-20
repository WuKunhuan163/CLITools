"""Step 4: Validate credentials by attempting to get an access token."""
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
                return {"ok": True, "token": token[:20] + "..."}
            return {"ok": False, "error": data.get("message", str(data))}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def build_step(frame, win):
    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _(
        "tutorial_step4_title",
        "Step 4: Validate & Complete"
    ), is_title=True)

    status_block = win.add_block(frame, pady=(10, 5))

    app_key = ""
    app_secret = ""
    if _CONFIG_FILE.exists():
        try:
            cfg = json.loads(_CONFIG_FILE.read_text())
            app_key = cfg.get("app_key", "")
            app_secret = cfg.get("app_secret", "")
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

    info_block = win.add_block(frame, pady=(5, 5))
    win.setup_label(info_block, f"Checking credentials for: **{app_key}**")

    result_block = win.add_block(frame, pady=(10, 10))
    result = _validate_credentials(app_key, app_secret)

    if result.get("ok"):
        result_label = tk.Label(
            result_block,
            text=_("tutorial_step4_success",
                   "Credentials validated successfully!\n\n"
                   "Token preview: {token}\n\n"
                   "Your configuration is saved and ready to use.\n\n"
                   "Available commands:\n"
                   "  DINGTALK status              Check status\n"
                   "  DINGTALK contact <phone>     Look up a contact\n"
                   "  DINGTALK send \"msg\" --phone <phone>\n\n"
                   "Make sure you've enabled API permissions (Step 3)\n"
                   "before using contact and messaging features.",
                   token=result.get("token", "?")),
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
            text=_("tutorial_step4_failed",
                   "Validation failed:\n{error}\n\n"
                   "Please check your credentials and try again.\n"
                   "Go back to Step 2 to update them.",
                   error=error_msg),
            font=get_label_style(),
            fg="#cc3333",
            bg=result_block.cget("bg"),
            justify="left",
            wraplength=600,
        )
        result_label.pack(anchor="w", padx=10)
        win.set_step_validated(False)
