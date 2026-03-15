import tkinter as tk
import json
from pathlib import Path
from interface.gui import get_label_style
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step3_title", "Step 3: Create a Service Account"), is_title=True)
    
    # Content Block
    content_block = win.add_block(frame)
    content = _(
        "tutorial_step3_content",
        "1. In the sidebar, go to 'APIs & Services' > 'Credentials'.\n\n"
        "2. Click 'Create Credentials' > 'Service Account'.\n\n"
        "3. Enter a name (e.g., 'drive-controller') and click 'Create and Continue'.\n\n"
        "4. (Important) At the 'Grant access' step, you can skip role selection or choose 'Project Editor' for ease of development.\n\n"
        "5. Copy the Service Account Email (e.g., xxx@your-project.iam.gserviceaccount.com) and paste it below."
    )
    win.setup_label(content_block, content)

    # Image Blocks
    for i in range(1, 3):
        img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
        if img_path.exists():
            img_block = win.add_block(frame)
            win.setup_image(img_block, img_path, upscale=2)

    # Service Account Email Input Block
    email_block = win.add_block(frame, pady=(15, 5))
    email_label = tk.Label(email_block, text=_("tutorial_step3_email_label", "Service Account Email:"), 
                           font=get_label_style(), bg=email_block.cget("bg"))
    email_label.pack(anchor="w", padx=10, pady=(0, 5))

    email_var = tk.StringVar(value="")
    email_entry = tk.Entry(email_block, textvariable=email_var, font=get_label_style(), width=50)
    email_entry.pack(fill=tk.X, padx=10, pady=(0, 5))

    status_var = tk.StringVar(value="")
    status_label = tk.Label(email_block, textvariable=status_var, 
                            font=get_label_style(), fg="gray", bg=email_block.cget("bg"))
    status_label.pack(anchor="w", padx=10, pady=(0, 5))

    def _get_config_path():
        project_root = getattr(win, "project_root", None)
        if not project_root:
            return None
        config_dir = project_root / "data" / "google_cloud_console"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "config.json"

    def _load_saved_email():
        config_path = _get_config_path()
        if config_path and config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    cfg = json.load(f)
                saved = cfg.get("service_account_email", "")
                if saved:
                    email_var.set(saved)
                    status_var.set(_("tutorial_step3_loaded_email", "Loaded saved email."))
                    status_label.config(fg="green")
                    win.set_step_validated(True)
            except Exception:
                pass

    def on_save_email():
        email = email_var.get().strip()
        if not email:
            status_var.set(_("tutorial_step3_invalid_email", "Please enter a valid email."))
            status_label.config(fg="red")
            win.set_step_validated(False)
            return
        if "@" not in email or "." not in email:
            status_var.set(_("tutorial_step3_invalid_format", "Invalid email format."))
            status_label.config(fg="red")
            win.set_step_validated(False)
            return

        config_path = _get_config_path()
        if config_path:
            cfg = {}
            if config_path.exists():
                try:
                    with open(config_path, 'r') as f:
                        cfg = json.load(f)
                except Exception:
                    pass
            cfg["service_account_email"] = email
            with open(config_path, 'w') as f:
                json.dump(cfg, f, indent=2)

        status_var.set(_("tutorial_step3_saved_email", "Saved: {email}", email=email))
        status_label.config(fg="green")
        win.set_step_validated(True)

    save_btn = tk.Button(email_block, text=_("tutorial_step3_save_btn", "Save Email"), command=on_save_email)
    save_btn.pack(anchor="w", padx=10, pady=(0, 10))

    _load_saved_email()

    win.set_step_validated(False)
    if email_var.get().strip():
        win.set_step_validated(True)
