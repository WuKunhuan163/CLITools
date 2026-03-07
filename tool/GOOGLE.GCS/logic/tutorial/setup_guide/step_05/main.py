import sys
import tkinter as tk
import threading
import time
from pathlib import Path
from logic.interface.gui import get_label_style, get_gui_colors
from logic.interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step5_title", "Step 5: Share Folders & Verify Access"), is_title=True)

    saved_email = ""
    project_root = getattr(win, "project_root", None)
    if project_root:
        email_cfg_path = project_root / "data" / "google_cloud_console" / "config.json"
        if email_cfg_path.exists():
            try:
                import json as _json
                with open(email_cfg_path, 'r') as f:
                    saved_email = _json.load(f).get("service_account_email", "")
            except Exception:
                pass

    email_display = saved_email if saved_email else "the Service Account Email from Step 3"

    content_block = win.add_block(frame)
    content = _(
        "tutorial_step5_content",
        "1. Open [Google Drive](https://drive.google.com/).\n\n"
        "2. Create two folders:\n"
        "   - **Root**: The main workspace folder for files, commands, and results.\n"
        "   - **Env**: A separate folder for environment state (virtual environments, command results, mount fingerprints).\n\n"
        "3. Right-click each folder > 'Share' > paste **{email}** > set 'Editor' > 'Share'.\n\n"
        "4. Copy each folder's ID from the URL (the part after `/folders/`) and paste below.",
        email=email_display
    )
    win.setup_label(content_block, content)

    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
        if img_path.exists():
            img_block = win.add_block(frame)
            win.setup_image(img_block, img_path, upscale=2)

    project_root = getattr(win, "project_root", None)
    existing_root_id = ""
    existing_env_id = ""
    if project_root:
        config_path = project_root / "data" / "config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                existing_root_id = cfg.get("root_folder_id", "")
                existing_env_id = cfg.get("env_folder_id", "")
            except Exception:
                pass

    input_block = win.add_block(frame, pady=(15, 5))
    bg = input_block.cget("bg")

    root_label = tk.Label(input_block, text=_("tutorial_step5_root_id_label", "Root Folder ID:"), font=get_label_style(), bg=bg)
    root_label.pack(anchor="w", padx=5)
    root_entry = tk.Entry(input_block, font=get_label_style(), width=50)
    root_entry.pack(fill=tk.X, padx=5, pady=(0, 8))
    if existing_root_id:
        root_entry.insert(0, existing_root_id)

    env_label = tk.Label(input_block, text=_("tutorial_step5_env_id_label", "Env Folder ID:"), font=get_label_style(), bg=bg)
    env_label.pack(anchor="w", padx=5)
    env_entry = tk.Entry(input_block, font=get_label_style(), width=50)
    env_entry.pack(fill=tk.X, padx=5, pady=(0, 8))
    if existing_env_id:
        env_entry.insert(0, existing_env_id)

    status_var = tk.StringVar(value=_("tutorial_step5_enter_ids", "Enter both folder IDs, then click Validate & Save."))
    status_label = tk.Label(input_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=5)

    btn_frame = tk.Frame(input_block, bg=bg)
    btn_frame.pack(pady=10)
    validate_btn = tk.Button(btn_frame, text=_("tutorial_step5_validate_btn", "Validate & Save"))
    validate_btn.pack()

    callback_queue = []

    def _process_callbacks():
        while callback_queue:
            fn = callback_queue.pop(0)
            try:
                fn()
            except Exception:
                pass
        try:
            if frame.winfo_exists():
                frame.after(100, _process_callbacks)
        except tk.TclError:
            pass

    frame.after(100, _process_callbacks)

    def on_validate():
        rid = root_entry.get().strip()
        eid = env_entry.get().strip()

        if not rid or not eid:
            status_var.set(_("tutorial_step5_ids_required", "Both folder IDs are required."))
            status_label.config(fg="red")
            win.set_step_validated(False)
            return

        validate_btn.config(state=tk.DISABLED, text=_("tutorial_step5_validating_btn", "Validating..."))
        status_var.set(_("tutorial_step5_validating_root", "Validating Root folder access..."))
        status_label.config(fg="black")
        frame.update_idletasks()

        def run_validation():
            try:
                import importlib.util
                auth_path = Path(__file__).resolve().parent.parent.parent.parent / "auth.py"
                spec = importlib.util.spec_from_file_location("gcs_auth_step5", str(auth_path))
                auth_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(auth_mod)

                ok_root, msg_root = auth_mod.validate_folder_access(project_root, rid)

                if not ok_root:
                    def on_fail_root():
                        status_var.set(_("tutorial_step5_root_error", "Root folder error: {msg}", msg=msg_root))
                        status_label.config(fg="red")
                        validate_btn.config(state=tk.NORMAL, text=_("tutorial_step5_validate_btn", "Validate & Save"))
                        win.set_step_validated(False)
                    callback_queue.append(on_fail_root)
                    return

                def update_env_status():
                    status_var.set(_("tutorial_step5_root_ok_validating_env", "Root OK ({msg}). Validating Env folder...", msg=msg_root))
                    frame.update_idletasks()
                callback_queue.append(update_env_status)
                time.sleep(0.3)

                ok_env, msg_env = auth_mod.validate_folder_access(project_root, eid)

                if not ok_env:
                    def on_fail_env():
                        status_var.set(_("tutorial_step5_env_error", "Env folder error: {msg}", msg=msg_env))
                        status_label.config(fg="red")
                        validate_btn.config(state=tk.NORMAL, text=_("tutorial_step5_validate_btn", "Validate & Save"))
                        win.set_step_validated(False)
                    callback_queue.append(on_fail_env)
                    return

                saved_path = auth_mod.save_gcs_config(project_root, rid, eid)

                def on_success():
                    status_var.set(_("tutorial_step5_success", "Validated and saved! Root: {root_msg}, Env: {env_msg}", root_msg=msg_root, env_msg=msg_env))
                    status_label.config(fg="green")
                    validate_btn.config(state=tk.NORMAL, text=_("tutorial_step5_validate_btn", "Validate & Save"))
                    win.set_step_validated(True)
                callback_queue.append(on_success)

            except Exception as e:
                def on_err():
                    status_var.set(_("tutorial_step5_error", "Error: {error}", error=str(e)))
                    status_label.config(fg="red")
                    validate_btn.config(state=tk.NORMAL, text=_("tutorial_step5_validate_btn", "Validate & Save"))
                    win.set_step_validated(False)
                callback_queue.append(on_err)

        threading.Thread(target=run_validation, daemon=True).start()

    validate_btn.config(command=on_validate)

    if existing_root_id and existing_env_id:
        status_var.set(_("tutorial_step5_preloaded", "Previous configuration loaded. Click Validate & Save to verify."))
        status_label.config(fg="gray")
    win.set_step_validated(False)
