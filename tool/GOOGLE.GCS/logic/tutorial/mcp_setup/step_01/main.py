"""Step 1: Detect and verify Google Chrome installation."""
import os
import sys
import tkinter as tk
import threading
from pathlib import Path
from logic.interface.gui import get_label_style, get_gui_colors
from logic.interface.lang import get_translation

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)
def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)


def _detect_chrome():
    """Detect Chrome installation. Returns (found, path_or_hint)."""
    if sys.platform == "darwin":
        path = "/Applications/Google Chrome.app"
        if os.path.exists(path):
            return True, path
        return False, "https://www.google.com/chrome/"
    elif sys.platform.startswith("linux"):
        import shutil
        for binary in ["google-chrome", "google-chrome-stable", "chromium-browser", "chromium"]:
            found = shutil.which(binary)
            if found:
                return True, found
        return False, "https://www.google.com/chrome/"
    elif sys.platform == "win32":
        paths = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ]
        for p in paths:
            if os.path.exists(p):
                return True, p
        return False, "https://www.google.com/chrome/"
    return False, "https://www.google.com/chrome/"


def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block,
        _("mcp_step1_title", "Step 1: Google Chrome"),
        is_title=True)

    content_block = win.add_block(frame)
    win.setup_label(content_block,
        _("mcp_step1_content",
          "MCP automation requires **Google Chrome** with remote debugging enabled.\n\n"
          "Click **Detect Chrome** to check if Chrome is installed on this machine."))

    action_block = win.add_block(frame, pady=(15, 5))
    bg = action_block.cget("bg")
    colors = get_gui_colors()

    status_var = tk.StringVar(value="")
    status_label = tk.Label(action_block, textvariable=status_var,
                            font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=(0, 8))

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

    def _on_detect():
        detect_btn.config(state="disabled", text=_("mcp_step1_detecting", "Detecting..."))
        status_var.set(_("mcp_step1_checking", "Checking for Chrome installation..."))

        def _work():
            found, path_or_hint = _detect_chrome()
            if found:
                def _ok():
                    status_var.set(_("mcp_step1_found", "Chrome found: {path}").format(path=path_or_hint))
                    status_label.config(fg=colors.get("success", "green"))
                    detect_btn.config(text=_("mcp_step1_detected", "Detected"), state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                def _fail():
                    status_var.set(_("mcp_step1_not_found",
                        "Chrome not found. Please install from: {url}").format(url=path_or_hint))
                    status_label.config(fg=colors.get("error", "red"))
                    detect_btn.config(
                        text=_("mcp_step1_retry", "Retry"),
                        state="normal")
                callback_queue.append(_fail)

        threading.Thread(target=_work, daemon=True).start()

    detect_btn = tk.Button(action_block,
        text=_("mcp_step1_detect_btn", "Detect Chrome"),
        command=_on_detect)
    detect_btn.pack(pady=(5, 0))

    # Auto-detect on step entry
    frame.after(500, _on_detect)
