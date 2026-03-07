"""Step 2: Launch debug Chrome and verify CDP connection."""
import os
import sys
import time
import tkinter as tk
import threading
from pathlib import Path
from interface.gui import get_label_style, get_gui_colors
from interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

CDP_PORT = 9222


def _is_cdp_available():
    try:
        from logic.chrome.session import is_chrome_cdp_available
        return is_chrome_cdp_available(CDP_PORT)
    except Exception:
        return False


def _get_debug_profile_dir():
    return os.path.expanduser("~/ChromeDebugProfile")


def _launch_chrome():
    """Launch Chrome with debug port. Returns True if CDP becomes available."""
    import subprocess
    profile = _get_debug_profile_dir()

    if sys.platform == "darwin":
        subprocess.Popen([
            "open", "-na", "Google Chrome", "--args",
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=*"
        ])
    elif sys.platform.startswith("linux"):
        import shutil
        for binary in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            if shutil.which(binary):
                subprocess.Popen([
                    binary,
                    f"--remote-debugging-port={CDP_PORT}",
                    f"--user-data-dir={profile}",
                    "--remote-allow-origins=*"
                ])
                break
        else:
            return False
    elif sys.platform == "win32":
        chrome_paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)
        if not chrome_exe:
            return False
        subprocess.Popen([
            chrome_exe,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=*"
        ])
    else:
        return False

    for _ in range(20):
        time.sleep(1)
        if _is_cdp_available():
            return True
    return False


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block,
        _("mcp_step2_title", "Step 2: CDP Connection"),
        is_title=True)

    content_block = win.add_block(frame)
    win.setup_label(content_block,
        _("mcp_step2_content",
          "Chrome must be running with **remote debugging** enabled (port {port}).\n\n"
          "Click **Launch Debug Chrome** to start a new Chrome instance with "
          "debugging, or **Check Connection** if Chrome is already running.").format(port=CDP_PORT))

    action_block = win.add_block(frame, pady=(15, 5))
    bg = action_block.cget("bg")
    colors = get_gui_colors()

    status_var = tk.StringVar(value="")
    status_label = tk.Label(action_block, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=(0, 8))

    btn_frame = tk.Frame(action_block, bg=bg)
    btn_frame.pack(pady=(5, 0))

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

    def _check_cdp():
        check_btn.config(state="disabled")
        launch_btn.config(state="disabled")
        status_var.set(_("mcp_step2_checking", "Checking CDP connection on port {port}...").format(port=CDP_PORT))

        def _work():
            ok = _is_cdp_available()
            if ok:
                def _ok():
                    status_var.set(_("mcp_step2_connected",
                        "Connected to Chrome CDP on port {port}.").format(port=CDP_PORT))
                    status_label.config(fg=colors.get("success", "green"))
                    check_btn.config(text=_("mcp_step2_connected_btn", "Connected"), state="disabled")
                    launch_btn.config(state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                def _fail():
                    status_var.set(_("mcp_step2_not_connected",
                        "Chrome CDP not available on port {port}.").format(port=CDP_PORT))
                    status_label.config(fg=colors.get("error", "red"))
                    check_btn.config(state="normal")
                    launch_btn.config(state="normal")
                callback_queue.append(_fail)

        threading.Thread(target=_work, daemon=True).start()

    def _on_launch():
        launch_btn.config(state="disabled", text=_("mcp_step2_launching", "Launching..."))
        check_btn.config(state="disabled")
        status_var.set(_("mcp_step2_starting", "Starting Chrome with debug port {port}...").format(port=CDP_PORT))

        def _work():
            ok = _launch_chrome()
            if ok:
                def _ok():
                    status_var.set(_("mcp_step2_launch_ok",
                        "Chrome launched and CDP connected on port {port}.").format(port=CDP_PORT))
                    status_label.config(fg=colors.get("success", "green"))
                    launch_btn.config(text=_("mcp_step2_launched", "Launched"), state="disabled")
                    check_btn.config(state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                def _fail():
                    status_var.set(_("mcp_step2_launch_fail",
                        "Chrome started but CDP not responding. "
                        "Try closing Chrome completely, then click Launch again."))
                    status_label.config(fg=colors.get("error", "red"))
                    launch_btn.config(
                        text=_("mcp_step2_launch_btn", "Launch Debug Chrome"),
                        state="normal")
                    check_btn.config(state="normal")
                callback_queue.append(_fail)

        threading.Thread(target=_work, daemon=True).start()

    check_btn = tk.Button(btn_frame,
        text=_("mcp_step2_check_btn", "Check Connection"),
        command=_check_cdp)
    check_btn.pack(side=tk.LEFT, padx=(0, 10))

    launch_btn = tk.Button(btn_frame,
        text=_("mcp_step2_launch_btn", "Launch Debug Chrome"),
        command=_on_launch)
    launch_btn.pack(side=tk.LEFT)

    # Auto-check on step entry
    frame.after(500, _check_cdp)
