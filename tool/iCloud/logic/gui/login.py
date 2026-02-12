import tkinter as tk
from pathlib import Path
import sys
import os
import json

# Fix shadowing: Remove script directory from sys.path[0] if present
script_path = Path(__file__).resolve()
if sys.path and sys.path[0] == str(script_path.parent):
    del sys.path[0]

# Add project root to sys.path to find 'logic' modules
project_root = script_path.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.style import get_label_style, get_gui_colors

class ICloudLoginWindow(BaseGUIWindow):
    def __init__(self, title, timeout, internal_dir):
        super().__init__(title, timeout, internal_dir, tool_name="iCloud")
        self.apple_id_entry = None
        self.password_entry = None

    def get_current_state(self):
        return {
            "apple_id": self.apple_id_entry.get().strip() if self.apple_id_entry else "",
            "password": self.password_entry.get() if self.password_entry else ""
        }

    def on_login(self):
        state = self.get_current_state()
        if not state["apple_id"] or not state["password"]:
            error_msg = self._("login_error_empty", "Please enter both Apple ID and password.")
            self.status_label.config(text=error_msg, fg=get_gui_colors()["red"])
            return
        
        self.finalize("success", state)

    def setup_ui(self):
        # Configure the main window
        self.root.geometry("400x280")
        
        # Bottom bar with countdown and buttons
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_login", "Login"),
            submit_cmd=self.on_login
        )

        main_frame = tk.Frame(self.root, padx=25, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title/Instruction
        tk.Label(main_frame, text=self._("login_instruction", "Sign in to iCloud"), 
                 font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Apple ID field
        tk.Label(main_frame, text=self._("label_apple_id", "Apple ID:"), 
                 font=get_label_style()).pack(anchor='w', pady=(0, 2))
        self.apple_id_entry = tk.Entry(main_frame, font=get_label_style())
        self.apple_id_entry.pack(fill=tk.X, pady=(0, 15))
        self.apple_id_entry.focus_set()

        # Password field
        tk.Label(main_frame, text=self._("label_password", "Password:"), 
                 font=get_label_style()).pack(anchor='w', pady=(0, 2))
        self.password_entry = tk.Entry(main_frame, font=get_label_style(), show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 10))

        # Bind Enter key to login
        self.root.bind('<Return>', lambda e: self.on_login())

        # Start standard GUI behaviors
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(1000, lambda: self.root.attributes("-topmost", False))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default="iCloud Login")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--internal-dir")
    args = parser.parse_args()

    # Configure environment for GUI
    from logic.gui.engine import setup_gui_environment
    setup_gui_environment()

    win = ICloudLoginWindow(args.title, args.timeout, args.internal_dir)
    win.run(win.setup_ui)
