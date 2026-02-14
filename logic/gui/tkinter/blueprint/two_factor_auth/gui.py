from pathlib import Path
import sys
from typing import Any, List, Optional
from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors

class TwoFactorAuthWindow(BaseGUIWindow):
    """
    Blueprint for Two-Factor Authentication (2FA) numeric code entry.
    Displays N separate boxes for a code.
    """
    def __init__(self, title, timeout, internal_dir, n=6, allowed_chars="0123456789", tool_name=None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "2FA")
        self.n = n
        self.allowed_chars = allowed_chars
        self.entries: List[Any] = []
        self.code_vars: List[Any] = []

    def get_current_state(self):
        """Returns the current entered code."""
        return "".join([v.get() for v in self.code_vars])

    def on_key_press(self, event, index):
        import tkinter as tk
        char = event.char
        
        if char in self.allowed_chars and char != "":
            self.code_vars[index].set(char)
            if index < self.n - 1:
                self.entries[index + 1].focus_set()
            return "break" # Prevent default behavior
        
        if event.keysym == "BackSpace":
            if self.code_vars[index].get() == "":
                if index > 0:
                    self.entries[index - 1].focus_set()
                    self.code_vars[index - 1].set("")
            else:
                self.code_vars[index].set("")
            return "break"
            
        if event.keysym == "Left":
            if index > 0:
                self.entries[index - 1].focus_set()
            return "break"
            
        if event.keysym == "Right":
            if index < self.n - 1:
                self.entries[index + 1].focus_set()
            return "break"

        # Allow Tab/Shift-Tab
        if event.keysym in ["Tab", "ISO_Left_Tab"]:
            return None
            
        return "break" # Block all other keys

    def on_submit(self):
        code = self.get_current_state()
        if len(code) < self.n:
            error_msg = self._("2fa_error_incomplete", "Please enter the full {n}-digit code.", n=self.n)
            self.status_label.config(text=error_msg, fg=get_gui_colors()["red"])
            return
        self.finalize("success", code)

    def setup_ui(self):
        import tkinter as tk
        self.root.geometry(f"{max(400, self.n * 60)}x250")
        
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_verify", "Verify"),
            submit_cmd=self.on_submit
        )

        main_frame = tk.Frame(self.root, padx=30, pady=30)
        main_frame.pack(fill=tk.BOTH, expand=True)

        instr = self._("2fa_instruction", "Enter the verification code")
        tk.Label(main_frame, text=instr, font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Container for the digits
        code_frame = tk.Frame(main_frame)
        code_frame.pack()

        for i in range(self.n):
            var = tk.StringVar()
            self.code_vars.append(var)
            
            # Create a boxy entry
            entry = tk.Entry(
                code_frame, 
                textvariable=var,
                width=2, 
                font=("Arial", 24, "bold"),
                justify='center',
                relief=tk.RIDGE,
                borderwidth=2
            )
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_key_press(e, idx))
            self.entries.append(entry)

        # Initial focus
        self.entries[0].focus_set()
        
        # Start timer and focus behavior
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)

