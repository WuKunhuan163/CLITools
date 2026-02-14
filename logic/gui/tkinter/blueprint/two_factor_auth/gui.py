from pathlib import Path
import sys
from typing import Any, List, Optional, Callable, Dict
from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors

class TwoFactorAuthWindow(BaseGUIWindow):
    """
    Blueprint for Two-Factor Authentication (2FA) numeric code entry.
    Displays N separate boxes for a code.
    """
    def __init__(self, title, timeout, internal_dir, n=6, allowed_chars="0123456789", tool_name=None, 
                 prompt_msg=None, verify_handler: Optional[Callable[[str], Dict[str, Any]]] = None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "2FA")
        self.n = n
        self.allowed_chars = allowed_chars
        self.entries: List[Any] = []
        self.code_vars: List[Any] = []
        self.prompt_msg_initial = prompt_msg
        self.error_label = None
        self.verify_handler = verify_handler
        self.attempt_count = 0
        self.max_attempts = 5
        self.verify_history = []

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

    def finalize(self, status: str, data: Any, reason: Optional[str] = None):
        """Unified closure point (Interface I) with history logging."""
        if not self.window_closed:
            # If we have a verification history and this is an error/cancel, include it
            if self.verify_history and status in ["error", "cancelled"]:
                history_str = "\n".join([f"Attempt {h['idx']}: {h['error']}" for h in self.verify_history])
                if isinstance(data, str) and data:
                    data = f"{data}\n\nHistory:\n{history_str}"
                elif data is None or not data:
                    data = f"History:\n{history_str}"
                elif isinstance(data, dict):
                    data["history"] = history_str
            
            super().finalize(status, data, reason=reason)

    def on_submit(self):
        code = self.get_current_state()
        if len(code) < self.n:
            error_msg = self._("2fa_error_incomplete", "Please enter the full {n}-digit code.", n=self.n)
            self.show_error(error_msg)
            return
            
        self.set_loading(True)
        
        if self.verify_handler:
            # Execute verification handler in a separate thread to keep UI responsive
            def do_verify():
                self.attempt_count += 1
                try:
                    res = self.verify_handler(code)
                    if res.get("status") == "success":
                        self.callback_queue.put(lambda: self.finalize("success", res.get("data", code)))
                    else:
                        err = res.get("message", "Unknown error")
                        self.verify_history.append({"idx": self.attempt_count, "error": err})
                        self.callback_queue.put(lambda: self.handle_verify_fail(err))
                except Exception as e:
                    err = str(e)
                    self.verify_history.append({"idx": self.attempt_count, "error": err})
                    self.callback_queue.put(lambda: self.handle_verify_fail(err))

            import threading
            threading.Thread(target=do_verify, daemon=True).start()
        else:
            # Give UI time to update
            self.root.after(100, lambda: self.finalize("success", code))

    def handle_verify_fail(self, error_msg: str):
        """Handle verification failure."""
        self.set_loading(False)
        full_error = f"Attempt {self.attempt_count}/{self.max_attempts}: {error_msg}"
        self.show_error(full_error)
        
        if self.attempt_count >= self.max_attempts:
            # Record history and exit
            history_str = "\n".join([f"Attempt {h['idx']}: {h['error']}" for h in self.verify_history])
            # Ensure final result is set before closing
            self.finalize("error", history_str, reason="max_attempts_exceeded")

    def set_loading(self, is_loading: bool):
        """Toggle loading state in UI."""
        self.timer_frozen = is_loading
        if is_loading:
            if self.submit_btn:
                self.submit_btn.config(state="disabled", text=self._("btn_verifying", "Verifying ..."))
            if self.cancel_btn: self.cancel_btn.pack_forget()
            if self.add_time_btn: self.add_time_btn.pack_forget()
            self.set_inputs_locked(True)
        else:
            if self.submit_btn:
                self.submit_btn.config(state="normal", text=self._("btn_verify", "Verify"))
            # Restore buttons in original order (packing right-to-left)
            if self.add_time_btn:
                self.add_time_btn.pack(side="right", padx=(0, 10))
            if self.cancel_btn: 
                self.cancel_btn.pack(side="right", padx=(0, 10))
            self.set_inputs_locked(False)

    def set_inputs_locked(self, locked: bool):
        """Lock/Unlock input fields."""
        state = "disabled" if locked else "normal"
        for entry in self.entries:
            entry.config(state=state)

    def show_error(self, message: str):
        """Display error message in the UI."""
        if self.error_label:
            self.error_label.config(text=message)
        else:
            self.status_label.config(text=message, fg=get_gui_colors()["red"])

    def setup_ui(self):
        import tkinter as tk
        self.root.geometry(f"{max(600, self.n * 80)}x320")
        
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
                borderwidth=2,
                insertontime=0 # Hide cursor
            )
            entry.pack(side=tk.LEFT, padx=5)
            entry.bind("<KeyPress>", lambda e, idx=i: self.on_key_press(e, idx))
            self.entries.append(entry)

        # Prompt/Error label area
        from logic.gui.tkinter.style import get_secondary_label_style
        self.error_label = tk.Label(main_frame, text="", font=get_secondary_label_style(), 
                                    fg=get_gui_colors()["red"], wraplength=550, justify="center")
        self.error_label.pack(pady=(20, 0))
        if self.prompt_msg_initial:
            self.error_label.config(text=self.prompt_msg_initial, fg="black") # Initial prompt is not red

        # Initial focus
        self.entries[0].focus_set()
        
        # Start timer and focus behavior
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)

