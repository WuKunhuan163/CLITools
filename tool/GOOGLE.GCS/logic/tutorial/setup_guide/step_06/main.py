"""Step 6: Verify Colab access via Google Drive API."""
import tkinter as tk
import threading
import json
from pathlib import Path
from interface.gui import get_label_style, get_gui_colors
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def _load_config(project_root):
    path = project_root / "data" / "config.json"
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def _get_auth_module(project_root):
    import importlib.util
    auth_path = Path(project_root) / "tool" / "GOOGLE.GCS" / "logic" / "auth.py"
    if not auth_path.exists():
        auth_path = Path(__file__).resolve().parent.parent.parent.parent / "auth.py"
    spec = importlib.util.spec_from_file_location("gcs_auth_step6", str(auth_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_drive_token(project_root):
    key_path = Path(project_root) / "data" / "google_cloud_console" / "console_key.json"
    if not key_path.exists():
        raise FileNotFoundError("Console key not found. Please complete Step 4.")
    with open(key_path, 'r') as f:
        info = json.load(f)
    auth_mod = _get_auth_module(project_root)
    return auth_mod.get_access_token(info, scope="https://www.googleapis.com/auth/drive")


def _verify_folder_access(token, folder_id):
    """Verify the service account can list files in the target folder."""
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": f"'{folder_id}' in parents and trashed = false",
              "fields": "files(id, name)", "pageSize": 5}
    res = requests.get("https://www.googleapis.com/drive/v3/files",
                       headers=headers, params=params, timeout=20)
    return res.status_code == 200


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step6_title", "Step 6: Verify Colab Access"), is_title=True)

    project_root = getattr(win, "project_root", None)
    env_folder_id = ""
    root_folder_id = ""
    if project_root:
        config_path = project_root / "data" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                    env_folder_id = cfg.get("env_folder_id", "")
                    root_folder_id = cfg.get("root_folder_id", "")
            except Exception:
                pass

    target_folder_id = env_folder_id or root_folder_id
    drive_link = f"https://drive.google.com/drive/folders/{target_folder_id}" if target_folder_id else "https://drive.google.com/"

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step6_content",
        "This step verifies that the service account can access your "
        "[Google Drive folder]({drive_link}).\n\n"
        "GCS uses any open Colab tab for remote execution -- "
        "no dedicated notebook file is needed.",
        drive_link=drive_link
    )
    win.setup_label(content_block, content)

    action_block = win.add_block(frame, pady=(15, 5))
    bg = action_block.cget("bg")
    get_gui_colors()

    status_var = tk.StringVar(value="")
    status_label = tk.Label(action_block, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=(0, 5))

    callback_queue = []

    def _process_callbacks():
        while callback_queue:
            fn = callback_queue.pop(0)
            try: fn()
            except Exception: pass
        try:
            if frame.winfo_exists():
                frame.after(100, _process_callbacks)
        except tk.TclError:
            pass

    frame.after(100, _process_callbacks)

    def _on_verify():
        verify_btn.config(state=tk.DISABLED, text=_("tutorial_step6_verifying_btn", "Verifying..."))
        status_var.set(_("tutorial_step6_checking", "Checking Drive API access..."))
        status_label.config(fg="black")
        frame.update_idletasks()

        def run_verify():
            try:
                token = _get_drive_token(project_root)
                if _verify_folder_access(token, target_folder_id):
                    def on_ok():
                        status_var.set(_("tutorial_step6_success", "Drive access verified."))
                        status_label.config(fg="green")
                        verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Access"))
                        win.set_step_validated(True)
                    callback_queue.append(on_ok)
                else:
                    def on_fail():
                        status_var.set(_(
                            "tutorial_step6_not_found",
                            "Cannot access the Drive folder. "
                            "Ensure the folder is shared with the service account."
                        ))
                        status_label.config(fg="red")
                        verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Access"))
                        win.set_step_validated(False)
                    callback_queue.append(on_fail)

            except Exception:
                def on_err():
                    status_var.set(_("tutorial_step6_error", "Error: {msg}", msg=str(e)))
                    status_label.config(fg="red")
                    verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Access"))
                callback_queue.append(on_err)

        threading.Thread(target=run_verify, daemon=True).start()

    verify_btn = tk.Button(frame, text=_("tutorial_step6_verify_btn", "Verify Access"),
                           command=_on_verify)
    verify_btn.pack(pady=(10, 10))

    if target_folder_id:
        frame.after(500, _on_verify)
    else:
        status_var.set(_("tutorial_step6_no_env", "No folder configured. Complete Step 5 first."))
        status_label.config(fg="red")
