"""Keyboard shortcut settings GUI and config management.

Settings are persisted to logic/config/keyboard.json so all tools
can access them via `load_settings()`.

The GUI uses macOS-style capture-based key assignment: click a field
to activate it, then press the desired key combo. Clicking elsewhere
locks the field.
"""
import json
import platform
import tkinter as tk
from pathlib import Path
from typing import Dict, Optional

_CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"
_SETTINGS_FILE = _CONFIG_DIR / "keyboard.json"

_DEFAULTS: Dict[str, str] = {
    "paste": "cmd+v" if platform.system() == "Darwin" else "ctrl+v",
    "confirm": "return",
}


def load_settings() -> Dict[str, str]:
    """Load user keyboard settings, falling back to defaults."""
    settings = dict(_DEFAULTS)
    if _SETTINGS_FILE.exists():
        try:
            with open(_SETTINGS_FILE, "r") as f:
                saved = json.load(f)
            settings.update(saved)
        except Exception:
            pass
    return settings


def save_settings(settings: Dict[str, str]):
    """Persist keyboard settings to logic/config/keyboard.json."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_paste_combo() -> str:
    """Return the paste shortcut string (e.g. 'cmd+v')."""
    return load_settings()["paste"]


def get_confirm_key() -> str:
    """Return the confirm/execute key name."""
    return load_settings()["confirm"]


class _KeyCaptureEntry(tk.Frame):
    """A macOS-style key capture field.

    Click to activate (highlight), then press any key/combo to assign.
    Click outside to deactivate. Shows the captured key name.
    """
    def __init__(self, parent, label: str, initial_value: str, **kwargs):
        super().__init__(parent, **kwargs)
        self._active = False
        self._value = initial_value

        self._label = tk.Label(self, text=label, font=("Menlo", 12, "bold"), width=12, anchor="w")
        self._label.pack(side=tk.LEFT, padx=(0, 8))

        self._display = tk.Label(
            self, text=initial_value, font=("Menlo", 12),
            relief=tk.SUNKEN, width=22, anchor="w", padx=6, pady=4,
            bg="white", fg="black"
        )
        self._display.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._display.bind("<Button-1>", self._activate)

    def _activate(self, event=None):
        self._active = True
        self._display.config(bg="#CCE5FF", text="Press a key...")
        self._display.focus_set()
        self._display.bind("<Key>", self._on_key)
        self._display.bind("<FocusOut>", self._deactivate)

    def _deactivate(self, event=None):
        if not self._active:
            return
        self._active = False
        self._display.config(bg="white", text=self._value)
        self._display.unbind("<Key>")
        self._display.unbind("<FocusOut>")

    def _on_key(self, event):
        if not self._active:
            return
        parts = []
        if event.state & 0x0008:
            parts.append("cmd" if platform.system() == "Darwin" else "meta")
        if event.state & 0x0004:
            parts.append("ctrl")
        if event.state & 0x0002:
            parts.append("alt" if platform.system() != "Darwin" else "option")
        if event.state & 0x0001:
            parts.append("shift")

        key_name = event.keysym.lower()
        # Skip lone modifier presses
        if key_name in ("meta_l", "meta_r", "control_l", "control_r",
                        "alt_l", "alt_r", "shift_l", "shift_r",
                        "super_l", "super_r", "caps_lock"):
            return

        if key_name not in parts:
            parts.append(key_name)

        combo = "+".join(parts) if parts else key_name
        self._value = combo
        self._active = False
        self._display.config(bg="#D4EDDA", text=combo)
        self._display.unbind("<Key>")
        self._display.after(600, lambda: self._display.config(bg="white"))

    @property
    def value(self) -> str:
        return self._value


def open_settings_gui(parent: Optional[tk.Tk] = None):
    """Open a tkinter GUI for configuring keyboard shortcuts.

    Uses macOS-style capture: click a field, press a key combo to assign it.
    """
    from logic.utils.accessibility.keyboard.monitor import is_available, check_accessibility_trusted

    standalone = parent is None
    if standalone:
        root = tk.Tk()
    else:
        root = tk.Toplevel(parent)

    root.title("Keyboard Shortcut Settings")
    root.geometry("480x260")
    root.resizable(False, False)

    settings = load_settings()

    # --- Status ---
    status_frame = tk.Frame(root, padx=14, pady=10)
    status_frame.pack(fill=tk.X)

    pynput_ok = is_available()
    access_ok = check_accessibility_trusted()
    capture_ok = pynput_ok and access_ok

    if capture_ok:
        status_text = "Keyboard capture: available"
        status_color = "green"
    elif pynput_ok and not access_ok:
        status_text = "Keyboard capture: needs Accessibility permission"
        status_color = "orange"
    else:
        status_text = "Keyboard capture: pynput not installed"
        status_color = "red"

    tk.Label(status_frame, text=status_text, font=("Menlo", 11, "bold"),
             fg=status_color).pack(anchor="w")

    if not capture_ok:
        tk.Label(status_frame,
                 text="Settings saved but only effective once capture works.",
                 font=("Menlo", 10), fg="gray").pack(anchor="w", pady=(2, 0))

    # --- Key capture fields ---
    form = tk.Frame(root, padx=14, pady=6)
    form.pack(fill=tk.BOTH, expand=True)

    paste_entry = _KeyCaptureEntry(form, "Paste:", settings.get("paste", _DEFAULTS["paste"]))
    paste_entry.pack(fill=tk.X, pady=4)

    confirm_entry = _KeyCaptureEntry(form, "Confirm:", settings.get("confirm", _DEFAULTS["confirm"]))
    confirm_entry.pack(fill=tk.X, pady=4)

    # --- Hint ---
    tk.Label(form, text="Click a field, then press desired key combination.",
             font=("Menlo", 10), fg="gray").pack(anchor="w", pady=(8, 0))

    # --- Buttons ---
    btn_frame = tk.Frame(root, padx=14, pady=10)
    btn_frame.pack(fill=tk.X)

    result_var = tk.StringVar(value="")

    def on_save():
        new_settings = {
            "paste": paste_entry.value,
            "confirm": confirm_entry.value,
        }
        save_settings(new_settings)
        result_var.set("Saved.")
        root.after(1500, lambda: result_var.set(""))

    def on_reset():
        save_settings(dict(_DEFAULTS))
        paste_entry._value = _DEFAULTS["paste"]
        paste_entry._display.config(text=_DEFAULTS["paste"])
        confirm_entry._value = _DEFAULTS["confirm"]
        confirm_entry._display.config(text=_DEFAULTS["confirm"])
        result_var.set("Reset to defaults.")
        root.after(1500, lambda: result_var.set(""))

    tk.Button(btn_frame, text="Save", command=on_save, font=("Menlo", 11),
              width=10).pack(side=tk.LEFT, padx=(0, 8))
    tk.Button(btn_frame, text="Reset Defaults", command=on_reset,
              font=("Menlo", 11), width=14).pack(side=tk.LEFT, padx=(0, 8))
    tk.Label(btn_frame, textvariable=result_var, font=("Menlo", 11, "bold"),
             fg="green").pack(side=tk.LEFT)

    if standalone:
        root.mainloop()


if __name__ == "__main__":
    open_settings_gui()
