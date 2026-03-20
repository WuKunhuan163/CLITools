"""Step 2: Get Client ID, Client Secret, and your phone number."""
import tkinter as tk
import json
import urllib.request
from pathlib import Path
from interface.gui import get_label_style
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
_TOOL_DIR = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_FILE = _TOOL_DIR / "data" / "config.json"


def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def _migrate_config(cfg):
    """Migrate flat config to phone-keyed accounts hierarchy if needed."""
    if "accounts" in cfg:
        return cfg
    if not cfg.get("app_key"):
        return cfg

    phone = cfg.get("phone", "default")
    account = {}
    for k in ("app_key", "app_secret", "agent_id", "operator_id",
              "webhook_url", "webhook_secret",
              "new_token", "new_token_expiry", "old_token", "old_token_expiry"):
        if k in cfg:
            account[k] = cfg.pop(k)

    cfg["accounts"] = {phone: account}
    cfg["active_phone"] = phone
    cfg.pop("phone", None)
    return cfg


def _save_cfg(cfg):
    _CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def _verify_token(app_key, app_secret):
    """Quick token check to verify credentials."""
    try:
        body = json.dumps({"appKey": app_key, "appSecret": app_secret}).encode()
        req = urllib.request.Request(
            "https://api.dingtalk.com/v1.0/oauth2/accessToken",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return bool(data.get("accessToken"))
    except Exception:
        return False


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _(
        "tutorial_step2_title",
        "Step 2: Credentials & Phone"
    ), is_title=True)

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step2_content",
        "1. In the [DingTalk Developer Console](https://open-dev.dingtalk.com/fe/app), "
        "select the app you created.\n\n"
        "2. Go to [AI & Robot](https://open-dev.dingtalk.com/fe/ai) in the sidebar, "
        "select your app, then navigate to **Credentials & Basic Info** (凭证与基础信息).\n\n"
        "3. Copy your **Client ID** (AppKey) and **Client Secret** (AppSecret) below.\n\n"
        "4. Enter your **DingTalk phone number** — this links credentials to your identity "
        "for multi-account management."
    )
    win.add_inline_links(content_block, content)

    input_block = win.add_block(frame, pady=(15, 5))

    # Phone number
    phone_label = tk.Label(input_block, text=_("label_phone", "Your DingTalk phone number:"),
                           font=get_label_style(), bg=input_block.cget("bg"))
    phone_label.pack(anchor="w", padx=10, pady=(5, 2))

    win._dt_phone_var = tk.StringVar(value="")
    phone_entry = tk.Entry(input_block, textvariable=win._dt_phone_var, font=get_label_style(), width=30)
    phone_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

    # Client ID
    key_label = tk.Label(input_block, text=_("label_client_id", "Client ID (AppKey):"),
                         font=get_label_style(), bg=input_block.cget("bg"))
    key_label.pack(anchor="w", padx=10, pady=(5, 2))

    win._dt_key_var = tk.StringVar(value="")
    key_entry = tk.Entry(input_block, textvariable=win._dt_key_var, font=get_label_style(), width=50)
    key_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

    # Client Secret
    secret_label = tk.Label(input_block, text=_("label_client_secret", "Client Secret (AppSecret):"),
                            font=get_label_style(), bg=input_block.cget("bg"))
    secret_label.pack(anchor="w", padx=10, pady=(5, 2))

    win._dt_secret_var = tk.StringVar(value="")
    secret_entry = tk.Entry(input_block, textvariable=win._dt_secret_var, font=get_label_style(), width=50, show="*")
    secret_entry.pack(fill=tk.X, padx=10, pady=(0, 10))

    # Status
    win._dt_status_var = tk.StringVar(value="")
    status_label = tk.Label(input_block, textvariable=win._dt_status_var,
                            font=get_label_style(), fg="gray", bg=input_block.cget("bg"))
    status_label.pack(anchor="w", padx=10, pady=(0, 5))

    def _load_saved():
        if not _CONFIG_FILE.exists():
            return
        try:
            cfg = json.loads(_CONFIG_FILE.read_text())
            cfg = _migrate_config(cfg)
            active = cfg.get("active_phone", "")
            if active and active != "default":
                win._dt_phone_var.set(active)
            acct = cfg.get("accounts", {}).get(active, {})
            if not acct:
                saved_key = cfg.get("app_key", "")
                saved_secret = cfg.get("app_secret", "")
            else:
                saved_key = acct.get("app_key", "")
                saved_secret = acct.get("app_secret", "")
            if saved_key:
                win._dt_key_var.set(saved_key)
            if saved_secret:
                win._dt_secret_var.set(saved_secret)
            if saved_key and saved_secret:
                win._dt_status_var.set(_("tutorial_step2_loaded", "Loaded saved credentials."))
                status_label.config(fg="green")
                win.set_step_validated(True)
        except Exception:
            pass

    def on_save():
        try:
            phone = win._dt_phone_var.get().strip().lstrip("+").lstrip("86")
            k = win._dt_key_var.get().strip()
            s = win._dt_secret_var.get().strip()

            if not phone:
                win._dt_status_var.set("Phone number is required.")
                status_label.config(fg="red")
                win.set_step_validated(False)
                return
            if not phone.isdigit() or len(phone) < 8:
                win._dt_status_var.set("Enter a valid phone number (digits only).")
                status_label.config(fg="red")
                win.set_step_validated(False)
                return
            if not k or not s:
                win._dt_status_var.set(_("tutorial_step2_empty", "All fields are required."))
                status_label.config(fg="red")
                win.set_step_validated(False)
                return
            if not k.startswith("ding"):
                win._dt_status_var.set(_("tutorial_step2_invalid_key", "Client ID should start with 'ding'."))
                status_label.config(fg="red")
                win.set_step_validated(False)
                return

            win._dt_status_var.set("Verifying credentials...")
            status_label.config(fg="gray")
            frame.update_idletasks()

            if not _verify_token(k, s):
                win._dt_status_var.set("Invalid credentials — token request failed.")
                status_label.config(fg="red")
                win.set_step_validated(False)
                return

            cfg = {}
            if _CONFIG_FILE.exists():
                try:
                    cfg = json.loads(_CONFIG_FILE.read_text())
                except Exception:
                    pass
            cfg = _migrate_config(cfg)

            accounts = cfg.setdefault("accounts", {})
            accounts[phone] = accounts.get(phone, {})
            accounts[phone]["app_key"] = k
            accounts[phone]["app_secret"] = s
            cfg["active_phone"] = phone
            # Keep flat keys for backward compat
            cfg["app_key"] = k
            cfg["app_secret"] = s
            _save_cfg(cfg)

            masked = s[:4] + "****" + s[-4:] if len(s) > 8 else "****"
            win._dt_status_var.set(f"Saved: {phone} -> {k} / {masked}")
            status_label.config(fg="green")
            win.set_step_validated(True)
        except Exception as e:
            win._dt_status_var.set(f"Error: {e}")
            status_label.config(fg="red")

    save_btn = tk.Button(input_block, text=_("tutorial_step2_save_btn", "Save Credentials"),
                         command=on_save, font=get_label_style())
    save_btn.pack(anchor="w", padx=10, pady=(5, 10))

    _load_saved()
