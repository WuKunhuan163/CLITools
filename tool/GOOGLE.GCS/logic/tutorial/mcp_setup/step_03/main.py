"""Step 3: Create or verify .root.ipynb notebook via CDP."""
import json
import time
import tkinter as tk
import threading
from pathlib import Path
from interface.gui import get_label_style, get_gui_colors
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

_DEFAULT_NOTEBOOK_NAME = ".root.ipynb"
CDP_PORT = 9222


def _get_notebook_name(project_root):
    cfg = _load_config(project_root)
    return cfg.get("root_notebook_name", _DEFAULT_NOTEBOOK_NAME)


def _load_config(project_root):
    path = project_root / "data" / "config.json"
    if not path.exists():
        return {}
    with open(path, 'r') as f:
        return json.load(f)


def _save_config(project_root, cfg):
    path = project_root / "data" / "config.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2)


def _check_existing_notebook(cfg):
    """Check if notebook ID is already configured. Returns (file_id, colab_url) or (None, None)."""
    nb_id = cfg.get("root_notebook_id", "")
    if nb_id:
        return nb_id, f"https://colab.research.google.com/drive/{nb_id}"
    return None, None


def _is_cdp_available():
    try:
        from logic.cdp.colab import is_chrome_cdp_available
        return is_chrome_cdp_available(CDP_PORT)
    except Exception:
        return False


def _has_colab_tab():
    try:
        from logic.cdp.colab import find_colab_tab
        return find_colab_tab(CDP_PORT) is not None
    except Exception:
        return False


def _create_notebook_via_cdp(folder_id, notebook_name=None):
    """Create notebook via CDP + gapi.client. Requires an open Colab tab."""
    try:
        from logic.cdp.colab import create_drive_file
        name = notebook_name or _DEFAULT_NOTEBOOK_NAME
        return create_drive_file(name, "colab", folder_id, port=CDP_PORT)
    except Exception as e:
        return {"success": False, "error": str(e)}


def _open_colab_tab(colab_url):
    """Open a Colab notebook URL in a new tab."""
    try:
        import urllib.request
        version_url = f"http://localhost:{CDP_PORT}/json/version"
        with urllib.request.urlopen(version_url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        browser_ws = data.get("webSocketDebuggerUrl")
        if not browser_ws:
            return False
        import websocket
        ws = websocket.create_connection(browser_ws, timeout=15)
        try:
            ws.send(json.dumps({"id": 1, "method": "Target.createTarget", "params": {"url": colab_url}}))
            ws.settimeout(10)
            for _ in range(20):
                resp = json.loads(ws.recv())
                if resp.get("id") == 1:
                    return bool(resp.get("result", {}).get("targetId"))
        finally:
            ws.close()
    except Exception:
        pass
    return False


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block,
        _("mcp_step3_title", "Step 3: Remote Notebook"),
        is_title=True)

    project_root = getattr(win, "project_root", None)
    cfg = _load_config(project_root) if project_root else {}
    env_folder_id = cfg.get("env_folder_id", "")
    root_folder_id = cfg.get("root_folder_id", "")
    target_folder_id = env_folder_id or root_folder_id

    content_block = win.add_block(frame)

    if not target_folder_id:
        win.setup_label(content_block,
            _("mcp_step3_no_folder",
              "No Google Drive folder configured. "
              "Please complete **GCS --setup-tutorial** first."))
        return

    notebook_name = _get_notebook_name(project_root) if project_root else _DEFAULT_NOTEBOOK_NAME
    drive_link = f"https://drive.google.com/drive/folders/{target_folder_id}"
    win.setup_label(content_block,
        _("mcp_step3_content",
          "GCS uses **{notebook}** in the [Env folder]({drive_link}) "
          "as the remote execution environment.\n\n"
          "This step will create the notebook via Chrome DevTools, "
          "or verify it if already configured.").format(
              notebook=notebook_name, drive_link=drive_link))

    action_block = win.add_block(frame, pady=(15, 5))
    bg = action_block.cget("bg")
    colors = get_gui_colors()

    status_var = tk.StringVar(value="")
    status_label = tk.Label(action_block, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=(0, 8))

    link_frame = tk.Frame(action_block, bg=bg)
    link_frame.pack(fill=tk.X, pady=(0, 5))

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

    def _show_colab_link(colab_url):
        import webbrowser
        for w in link_frame.winfo_children():
            w.destroy()
        link_label = tk.Label(link_frame,
            text=colab_url,
            font=get_label_style(), fg="blue", cursor="hand2", bg=bg)
        link_label.pack(anchor=tk.CENTER)
        link_label.bind("<Button-1>", lambda e: webbrowser.open(colab_url))

    def _on_create():
        create_btn.config(state="disabled", text=_("mcp_step3_creating", "Creating..."))
        status_var.set(_("mcp_step3_working", "Working..."))
        status_label.config(fg="gray")

        def _work():
            # Check if already exists
            nb_id, colab_url = _check_existing_notebook(cfg)
            if nb_id:
                def _existing():
                    status_var.set(_("mcp_step3_already_exists",
                        "Notebook already configured."))
                    status_label.config(fg=colors.get("success", "green"))
                    _show_colab_link(colab_url)
                    create_btn.config(text=_("mcp_step3_configured", "Configured"), state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_existing)
                return

            # Need a Colab tab open for gapi.client access
            if not _has_colab_tab():
                def _no_tab():
                    status_var.set(_("mcp_step3_opening_tab",
                        "Opening a Colab tab for API access..."))
                callback_queue.append(_no_tab)

                blank_url = "https://colab.research.google.com/#create=true"
                _open_colab_tab(blank_url)
                time.sleep(8)

                if not _has_colab_tab():
                    def _tab_fail():
                        status_var.set(_("mcp_step3_no_tab",
                            "Could not open Colab tab. Please open any Colab notebook "
                            "in the debug Chrome, then retry."))
                        status_label.config(fg=colors.get("error", "red"))
                        create_btn.config(
                            text=_("mcp_step3_retry", "Retry"),
                            state="normal")
                    callback_queue.append(_tab_fail)
                    return

            def _creating():
                status_var.set(_("mcp_step3_creating_nb",
                    "Creating {notebook} via CDP...").format(notebook=notebook_name))
            callback_queue.append(_creating)

            result = _create_notebook_via_cdp(target_folder_id, notebook_name)

            if result.get("success"):
                file_id = result["file_id"]
                colab_url = result.get("colab_url", f"https://colab.research.google.com/drive/{file_id}")
                cfg["root_notebook_id"] = file_id
                cfg["root_notebook_url"] = colab_url
                if project_root:
                    _save_config(project_root, cfg)

                _open_colab_tab(colab_url)

                def _ok():
                    status_var.set(_("mcp_step3_created",
                        "Notebook created and saved to config."))
                    status_label.config(fg=colors.get("success", "green"))
                    _show_colab_link(colab_url)
                    create_btn.config(text=_("mcp_step3_done", "Done"), state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                err = result.get("error", "Unknown error")
                def _fail():
                    status_var.set(_("mcp_step3_create_failed",
                        "Failed to create notebook: {error}").format(error=err))
                    status_label.config(fg=colors.get("error", "red"))
                    create_btn.config(
                        text=_("mcp_step3_retry", "Retry"),
                        state="normal")
                callback_queue.append(_fail)

        threading.Thread(target=_work, daemon=True).start()

    create_btn = tk.Button(action_block,
        text=_("mcp_step3_create_btn", "Create / Verify Notebook"),
        command=_on_create)
    create_btn.pack(pady=(5, 0))

    # Auto-run on step entry
    frame.after(500, _on_create)
