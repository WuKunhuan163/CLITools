"""Step 3: Verify Colab tab is accessible via CDP."""
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


def _has_colab_tab():
    try:
        from tool.GOOGLE.interface.main import find_colab_tab
        return find_colab_tab(CDP_PORT) is not None
    except Exception:
        return False


def _open_colab_tab():
    """Open the default Colab page in a new tab."""
    try:
        import json
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
            ws.send(json.dumps({
                "id": 1,
                "method": "Target.createTarget",
                "params": {"url": "https://colab.research.google.com/"}
            }))
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
        _("mcp_step3_title", "Step 3: Verify Colab Tab"),
        is_title=True)

    content_block = win.add_block(frame)
    win.setup_label(content_block,
        _("mcp_step3_content",
          "GDS uses any open Google Colab tab for remote execution.\n\n"
          "This step verifies that a Colab tab is accessible via "
          "Chrome DevTools. If none is open, one will be created."))

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

    def _on_verify():
        verify_btn.config(state="disabled", text=_("mcp_step3_checking_btn", "Checking..."))
        status_var.set(_("mcp_step3_working", "Checking for Colab tab..."))
        status_label.config(fg="gray")

        def _work():
            if _has_colab_tab():
                def _found():
                    status_var.set(_("mcp_step3_found",
                        "Colab tab detected. Ready for automation."))
                    status_label.config(fg=colors.get("success", "green"))
                    verify_btn.config(text=_("mcp_step3_done", "Verified"), state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_found)
                return

            def _opening():
                status_var.set(_("mcp_step3_opening",
                    "No Colab tab found. Opening one..."))
            callback_queue.append(_opening)

            _open_colab_tab()
            time.sleep(8)

            if _has_colab_tab():
                def _ok():
                    status_var.set(_("mcp_step3_opened",
                        "Colab tab opened and detected."))
                    status_label.config(fg=colors.get("success", "green"))
                    verify_btn.config(text=_("mcp_step3_done", "Verified"), state="disabled")
                    win.set_step_validated(True)
                callback_queue.append(_ok)
            else:
                def _fail():
                    status_var.set(_("mcp_step3_no_tab",
                        "Could not open Colab tab. Please open any Colab notebook "
                        "in the debug Chrome, then retry."))
                    status_label.config(fg=colors.get("error", "red"))
                    verify_btn.config(
                        text=_("mcp_step3_retry", "Retry"),
                        state="normal")
                callback_queue.append(_fail)

        threading.Thread(target=_work, daemon=True).start()

    verify_btn = tk.Button(action_block,
        text=_("mcp_step3_verify_btn", "Verify Colab Tab"),
        command=_on_verify)
    verify_btn.pack(pady=(5, 0))

    frame.after(500, _on_verify)
