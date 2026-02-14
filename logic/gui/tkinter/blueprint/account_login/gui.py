from pathlib import Path
import sys
from typing import Any

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/account_login/gui.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors

class AccountLoginWindow(BaseGUIWindow):
    """
    Blueprint for Account/Password login interactions.
    Inherits from the timed_bottom_bar blueprint for standardized behavior.
    """
    def __init__(self, title, timeout, internal_dir, tool_name=None, 
                 instruction_text=None, account_label=None, password_label=None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "LOGIN")
        self.instruction_text = instruction_text
        self.account_label = account_label
        self.password_label = password_label
        self.account_entry = None
        self.password_entry = None

    def get_current_state(self):
        """Returns the current input state (account and password)."""
        return {
            "account": self.account_entry.get().strip() if self.account_entry else "",
            "password": self.password_entry.get() if self.password_entry else ""
        }

    def on_submit(self):
        """Validates input and finalizes the window state."""
        state = self.get_current_state()
        if not state["account"] or not state["password"]:
            error_msg = self._("login_error_empty", "Please enter both credentials.")
            self.status_label.config(text=error_msg, fg=get_gui_colors()["red"])
            return
        self.finalize("success", state)

    def setup_ui(self):
        """Builds the Account/Password login interface."""
        import tkinter as tk
        self.root.geometry("400x300")
        
        # Initialize bottom bar from timed_bottom_bar
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_login", "Login"),
            submit_cmd=self.on_submit
        )

        main_frame = tk.Frame(self.root, padx=25, pady=25)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header / Instruction
        instr = self.instruction_text or self._("login_instruction", "Please sign in")
        tk.Label(main_frame, text=instr, font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Account input
        acc_lbl_text = self.account_label or self._("label_account", "Account:")
        tk.Label(main_frame, text=acc_lbl_text, font=get_label_style()).pack(anchor='w', pady=(0, 2))
        self.account_entry = tk.Entry(main_frame, font=get_label_style())
        self.account_entry.pack(fill=tk.X, pady=(0, 15))
        self.account_entry.focus_set()

        # Password input (masked)
        pw_lbl_text = self.password_label or self._("label_password", "Password:")
        tk.Label(main_frame, text=pw_lbl_text, font=get_label_style()).pack(anchor='w', pady=(0, 2))
        self.password_entry = tk.Entry(main_frame, font=get_label_style(), show="*")
        self.password_entry.pack(fill=tk.X, pady=(0, 10))

        # Bindings
        self.root.bind('<Return>', lambda e: self.on_submit())
        
        # Start timer and focus
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.after(1000, lambda: self.root.attributes("-topmost", False))

