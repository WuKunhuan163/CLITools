import tkinter as tk
import json
import threading
from pathlib import Path
from logic.lang.utils import get_translation
from logic.gui.tkinter.style import get_label_style

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent.parent)

def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def build_step(frame, win):
    win.set_step_validated(False)

    title_block = win.add_block(frame, pady=(20, 10))
    win.setup_label(title_block, _("tutorial_step2_title", "Step 2: Configure & Test Your Key"), is_title=True)

    desc_block = win.add_block(frame)
    win.setup_label(desc_block,
        _("tutorial_step2_desc", "Paste your Tavily API key below and click 'Validate' to test it."))

    tool_data_dir = _get_tool_data_dir()
    config = _load_config(tool_data_dir)

    input_block = win.add_block(frame, pady=(15, 5))
    bg = input_block.cget("bg")

    key_label = tk.Label(input_block, text=_("tutorial_api_key_label", "API Key:"), font=get_label_style(), bg=bg)
    key_label.pack(anchor="w", padx=5)

    entry_var = tk.StringVar()
    entry = tk.Entry(input_block, textvariable=entry_var, font=get_label_style(), width=50, show="*")
    entry.pack(fill=tk.X, padx=5, pady=(0, 8))

    if config.get("api_key"):
        entry_var.set(config["api_key"])

    status_var = tk.StringVar(value=_("tutorial_step2_enter_key", "Enter your API key, then click Validate."))
    status_label = tk.Label(input_block, textvariable=status_var, font=get_label_style(), fg="gray", bg=bg, wraplength=600)
    status_label.pack(pady=5)

    btn_frame = tk.Frame(input_block, bg=bg)
    btn_frame.pack(pady=10)
    validate_btn = tk.Button(btn_frame, text=_("tutorial_validate_btn", "Validate"))
    validate_btn.pack()

    def validate():
        key = entry_var.get().strip()
        if not key:
            status_var.set(_("tutorial_enter_api_key", "Please enter an API key."))
            status_label.config(fg="red")
            return

        status_var.set(_("tutorial_validating", "Validating..."))
        status_label.config(fg="blue")
        validate_btn.config(state=tk.DISABLED, text=_("tutorial_validating", "Validating..."))
        frame.update_idletasks()

        def do_validate():
            ok, msg = _test_api_key(key)
            callback_queue.append(lambda: _on_result(ok, msg, key))

        def _on_result(ok, msg, key):
            validate_btn.config(state=tk.NORMAL, text=_("tutorial_validate_btn", "Validate"))
            if ok:
                status_var.set(_("tutorial_valid", "Valid. {msg}", msg=msg))
                status_label.config(fg="green")
                _save_config(tool_data_dir, {"api_key": key})
                win.set_step_validated(True)
            else:
                status_var.set(_("tutorial_failed", "Failed: {msg}", msg=msg))
                status_label.config(fg="red")
                win.set_step_validated(False)

        threading.Thread(target=do_validate, daemon=True).start()

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

    validate_btn.config(command=validate)

    if config.get("api_key"):
        win.set_step_validated(True)
        status_var.set(_("tutorial_prev_key_loaded", "Previously configured key loaded."))
        status_label.config(fg="green")


def _get_tool_data_dir():
    curr = Path(__file__).resolve().parent
    while curr.name != "TAVILY" and curr != curr.parent:
        curr = curr.parent
    return curr / "data"


def _load_config(data_dir):
    config_path = data_dir / "config.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_config(data_dir, config):
    config_path = data_dir / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    existing = _load_config(data_dir)
    existing.update(config)
    with open(config_path, "w") as f:
        json.dump(existing, f, indent=2)


def _test_api_key(key):
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=key)
        client.search("test query", max_results=1, timeout=15)
        return True, _("tutorial_api_key_valid", "Tavily API key is valid.")
    except Exception as e:
        return False, str(e)
