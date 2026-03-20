"""
Bottom Bar Blueprint - A minimal GUI window with Cancel/Save action buttons.

This is a foundational blueprint that provides a simple bottom bar with
Cancel and Save (or custom primary action) buttons, plus an optional
status label. Unlike timed_bottom_bar, this blueprint has no countdown
timer, no "Add Time" button, and no periodic focus/bell behavior.

Inheritance:
    BaseGUIWindow (base.py) -> BottomBarWindow (this file)

Use this as a base class when building GUIs that need a persistent
action bar but not the timed interaction model.
"""
import sys
from pathlib import Path
from typing import Any, Optional, Callable

_script_path = Path(__file__).resolve()
_project_root = _script_path.parent.parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic._.gui.tkinter.blueprint.base import BaseGUIWindow
from logic._.gui.tkinter.style import get_button_style, get_status_style


def setup_bottom_bar(parent, window_instance: BaseGUIWindow,
                     save_text: str = "Save",
                     save_cmd: Callable = None,
                     cancel_text: str = "Cancel",
                     cancel_cmd: Callable = None) -> Any:
    """
    Creates a minimal bottom bar with status label, Cancel, and Save buttons.
    Returns: status_label widget.
    """
    import tkinter as tk

    bottom_frame = tk.Frame(parent)
    window_instance.bottom_bar_frame = bottom_frame
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(5, 15))

    status_label = tk.Label(bottom_frame, text="", font=get_status_style())
    status_label.pack(side=tk.LEFT)

    if save_cmd is None:
        save_cmd = lambda: window_instance.finalize("success", window_instance.get_current_state())

    save_btn = tk.Button(bottom_frame, text=save_text, command=save_cmd,
                         font=get_button_style(primary=True))
    save_btn.pack(side=tk.RIGHT)
    window_instance.submit_btn = save_btn

    if cancel_cmd is None:
        cancel_cmd = lambda: window_instance.finalize("cancelled", window_instance.get_current_state())

    cancel_btn = tk.Button(bottom_frame, text=cancel_text, command=cancel_cmd,
                           font=get_button_style())
    cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
    window_instance.cancel_btn = cancel_btn

    return status_label


class BottomBarWindow(BaseGUIWindow):
    """
    A GUI window with a minimal Cancel/Save bottom bar.

    Subclasses should override:
        - get_current_state() -> returns the data to pass back on save
        - setup_content(parent_frame) -> build the main UI content area
    """
    def __init__(self, title: str, internal_dir: str, tool_name: str = None,
                 save_text: str = "Save", cancel_text: str = "Cancel",
                 window_size: str = "500x400"):
        super().__init__(title, timeout=0, internal_dir=internal_dir,
                         tool_name=tool_name, focus_interval=0)
        self.save_text = save_text
        self.cancel_text = cancel_text
        self.window_size = window_size
        self.status_label = None

    def setup_content(self, parent_frame):
        """Override in subclasses to build the main content area."""
        pass

    def on_save(self):
        self.finalize("success", self.get_current_state())

    def setup_ui(self):
        import tkinter as tk
        self.root.geometry(self.window_size)
        self.root.resizable(True, True)

        self.status_label = setup_bottom_bar(
            self.root, self,
            save_text=self.save_text,
            save_cmd=self.on_save,
            cancel_text=self.cancel_text,
        )

        self.main_frame = tk.Frame(self.root, padx=15, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_content(self.main_frame)

    def run(self, custom_id: Optional[str] = None):
        super().run(self.setup_ui, custom_id=custom_id)
