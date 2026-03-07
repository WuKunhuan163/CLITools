import tkinter as tk
import threading
import json
import time
from pathlib import Path
from logic.interface.gui import get_label_style, get_gui_colors
from logic.interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

NOTEBOOK_NAME = ".root.ipynb"


def _build_notebook_json():
    return json.dumps({
        "cells": [
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": [
                    "# GCS Remote Root Notebook\n",
                    "import os, sys\n",
                    "print(f'Python {sys.version}')\n",
                    "print(f'CWD: {os.getcwd()}')\n",
                    "print('GCS root notebook ready.')"
                ]
            }
        ],
        "metadata": {
            "colab": {"provenance": []},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"}
        },
        "nbformat": 4,
        "nbformat_minor": 0
    }, indent=1)


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


def _find_notebook_in_folder(token, folder_id):
    import requests
    headers = {"Authorization": f"Bearer {token}"}
    q = f"'{folder_id}' in parents and name = '{NOTEBOOK_NAME}' and trashed = false"
    params = {"q": q, "fields": "files(id, name)", "pageSize": 5}
    res = requests.get("https://www.googleapis.com/drive/v3/files",
                       headers=headers, params=params, timeout=20)
    if res.status_code == 200:
        files = res.json().get("files", [])
        if files:
            return files[0]["id"]
    return None


def _try_create_notebook(token, target_folder_id):
    """
    Two-step approach:
    1. Create a metadata-only native Colab file (bypasses SA storage quota).
    2. PATCH content onto it. If PATCH fails, delete the empty file and report failure.
    Returns (success, file_id_or_error).
    """
    import requests

    metadata = {
        "name": NOTEBOOK_NAME,
        "parents": [target_folder_id],
        "mimeType": "application/vnd.google.colaboratory"
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    res = requests.post(
        "https://www.googleapis.com/drive/v3/files?supportsAllDrives=true",
        headers=headers,
        data=json.dumps(metadata),
        timeout=20
    )

    if res.status_code not in (200, 201):
        try:
            err_msg = res.json().get("error", {}).get("message", res.text[:200])
        except Exception:
            err_msg = res.text[:200]
        return False, f"Create failed ({res.status_code}): {err_msg}"

    file_id = res.json().get("id", "")
    if not file_id:
        return False, "Create returned no file ID."

    nb_json = _build_notebook_json()
    update_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    patch_res = requests.patch(
        f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media",
        headers=update_headers,
        data=nb_json.encode("utf-8"),
        timeout=20
    )

    if patch_res.status_code in (200, 201):
        return True, file_id

    # PATCH failed — clean up the empty file
    try:
        requests.delete(
            f"https://www.googleapis.com/drive/v3/files/{file_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10
        )
    except Exception:
        pass

    try:
        err_msg = patch_res.json().get("error", {}).get("message", patch_res.text[:200])
    except Exception:
        err_msg = patch_res.text[:200]
    return False, f"Content update failed ({patch_res.status_code}): {err_msg}"


def _save_notebook_config(project_root, file_id):
    colab_url = f"https://colab.research.google.com/drive/{file_id}"
    cfg_path = Path(project_root) / "data" / "config.json"
    cfg = {}
    if cfg_path.exists():
        try:
            with open(cfg_path, 'r') as f:
                cfg = json.load(f)
        except Exception:
            pass
    cfg["root_notebook_id"] = file_id
    cfg["root_notebook_url"] = colab_url
    with open(cfg_path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)
    return colab_url


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step6_title", "Step 6: Create Remote Notebook"), is_title=True)

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
        "GCS uses a Colab notebook (**{notebook}**) in your "
        "[Env folder]({drive_link}) as the remote execution environment.\n\n"
        "The system will attempt to create this notebook automatically.",
        notebook=NOTEBOOK_NAME,
        drive_link=drive_link
    )
    win.setup_label(content_block, content)

    action_block = win.add_block(frame, pady=(15, 5))
    bg = action_block.cget("bg")

    status_var = tk.StringVar(value="")
    status_label = tk.Label(action_block, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=(0, 5))

    link_frame = tk.Frame(action_block, bg=bg)
    link_frame.pack(fill=tk.X, pady=(0, 5))

    manual_frame = tk.Frame(frame, bg=frame.cget("bg"))
    manual_frame.pack(fill=tk.X)

    verify_btn = tk.Button(frame, text=_("tutorial_step6_verify_btn", "Verify Notebook"))

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

    def _show_colab_link(colab_url):
        import webbrowser
        for w in link_frame.winfo_children():
            w.destroy()
        link_label = tk.Label(
            link_frame,
            text=colab_url,
            font=get_label_style(), fg="blue", cursor="hand2",
            bg=bg, wraplength=600
        )
        link_label.pack(pady=2)
        link_label.bind("<Button-1>", lambda e: webbrowser.open_new(colab_url))

    def _show_manual_fallback(error_reason=""):
        for w in manual_frame.winfo_children():
            w.destroy()
        verify_btn.pack_forget()

        if error_reason:
            reason_block = win.add_block(manual_frame, pady=(5, 5))
            reason_label = tk.Label(
                reason_block,
                text=_("tutorial_step6_fail_reason", "Reason: {reason}", reason=error_reason),
                font=get_label_style(), fg="#888", bg=reason_block.cget("bg"), wraplength=600
            )
            reason_label.pack(anchor="w")

        manual_content = _(
            "tutorial_step6_manual_instructions",
            "You can create the notebook manually:\n"
            "1. Open your [Env folder]({drive_link}) in Google Drive.\n"
            "2. Right-click > **More** > **Google Colaboratory** to create a new notebook.\n"
            "3. Rename the notebook to **{notebook}**.\n\n"
            "Then click **Verify Notebook** below.",
            drive_link=drive_link,
            notebook=NOTEBOOK_NAME
        )
        win.setup_label(manual_frame, manual_content)

        for i in range(1, 3):
            img_path = Path(__file__).resolve().parent / "asset" / "image" / f"guide_{i}.png"
            if img_path.exists():
                img_block = win.add_block(manual_frame, pady=(5, 5))
                win.setup_image(img_block, img_path, upscale=2)

        verify_btn.pack(pady=(10, 10))

    def _on_success(file_id):
        colab_url = _save_notebook_config(project_root, file_id)
        status_var.set(_("tutorial_step6_success", "Notebook created successfully."))
        status_label.config(fg="green")
        _show_colab_link(colab_url)
        for w in manual_frame.winfo_children():
            w.destroy()
        verify_btn.pack_forget()
        win.set_step_validated(True)

    def _verify_notebook():
        if not target_folder_id:
            status_var.set(_("tutorial_step6_no_env", "Env folder ID not found. Complete Step 5 first."))
            status_label.config(fg="red")
            return

        verify_btn.config(state=tk.DISABLED, text=_("tutorial_step6_verifying_btn", "Verifying..."))
        status_var.set(_("tutorial_step6_checking", "Checking for notebook in Env folder..."))
        status_label.config(fg="black")
        frame.update_idletasks()

        def run_verify():
            try:
                token = _get_drive_token(project_root)
                file_id = _find_notebook_in_folder(token, target_folder_id)

                if file_id:
                    def on_found():
                        _on_success(file_id)
                        verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Notebook"))
                    callback_queue.append(on_found)
                else:
                    def on_not_found():
                        status_var.set(_(
                            "tutorial_step6_not_found",
                            "Notebook **{notebook}** not found in Env folder. Please create it manually.",
                            notebook=NOTEBOOK_NAME
                        ))
                        status_label.config(fg="red")
                        verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Notebook"))
                        win.set_step_validated(False)
                    callback_queue.append(on_not_found)

            except Exception as e:
                def on_err():
                    status_var.set(_("tutorial_step6_error", "Error: {msg}", msg=str(e)))
                    status_label.config(fg="red")
                    verify_btn.config(state=tk.NORMAL, text=_("tutorial_step6_verify_btn", "Verify Notebook"))
                callback_queue.append(on_err)

        threading.Thread(target=run_verify, daemon=True).start()

    def _attempt_upload():
        if not target_folder_id:
            status_var.set(_("tutorial_step6_no_env", "Env folder ID not found. Complete Step 5 first."))
            status_label.config(fg="red")
            return

        status_var.set(_("tutorial_step6_uploading", "Uploading notebook to Google Drive..."))
        status_label.config(fg="black")
        frame.update_idletasks()

        def run_upload():
            try:
                token = _get_drive_token(project_root)

                existing_id = _find_notebook_in_folder(token, target_folder_id)
                if existing_id:
                    def on_exists():
                        _on_success(existing_id)
                    callback_queue.append(on_exists)
                    return

                ok, result = _try_create_notebook(token, target_folder_id)

                if ok:
                    def on_uploaded():
                        _on_success(result)
                    callback_queue.append(on_uploaded)
                else:
                    def on_fail():
                        status_var.set(_(
                            "tutorial_step6_auto_failed",
                            "Automatic upload unavailable. Please create the notebook manually."
                        ))
                        status_label.config(fg="#996600")
                        _show_manual_fallback(result)
                        win.set_step_validated(False)
                    callback_queue.append(on_fail)

            except Exception as e:
                def on_err():
                    status_var.set(_(
                        "tutorial_step6_auto_failed",
                        "Automatic upload unavailable. Please create the notebook manually."
                    ))
                    status_label.config(fg="#996600")
                    _show_manual_fallback(str(e))
                    win.set_step_validated(False)
                callback_queue.append(on_err)

        threading.Thread(target=run_upload, daemon=True).start()

    verify_btn.config(command=_verify_notebook)

    existing_nb_id = ""
    if project_root:
        cfg_path = project_root / "data" / "config.json"
        if cfg_path.exists():
            try:
                with open(cfg_path, 'r') as f:
                    existing_nb_id = json.load(f).get("root_notebook_id", "")
            except Exception:
                pass

    if existing_nb_id:
        colab_url = f"https://colab.research.google.com/drive/{existing_nb_id}"
        _show_colab_link(colab_url)
        status_var.set(_("tutorial_step6_already_exists", "Notebook already configured."))
        status_label.config(fg="green")
        win.set_step_validated(True)
    else:
        _attempt_upload()
