from pathlib import Path
import sys
import threading
from typing import Any, Optional, Callable, Dict

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/account_login/gui.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic._.gui.tkinter.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
from logic._.gui.tkinter.style import get_label_style, get_gui_colors

class AccountLoginWindow(BaseGUIWindow):
    """
    Blueprint for Account/Password login interactions.
    Inherits from the timed_bottom_bar blueprint for standardized behavior.
    """
    def __init__(self, title, timeout, internal_dir, tool_name=None, 
                 instruction_text=None, account_label=None, password_label=None,
                 error_msg=None, lock_account=False,
                 verify_handler: Optional[Callable[[Dict[str, str]], Dict[str, Any]]] = None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "LOGIN")
        self.instruction_text = instruction_text
        self.account_label = account_label
        self.password_label = password_label
        self.lock_account = lock_account
        self.account_entry = None
        self.password_entry = None
        self.submit_btn = None
        self.account_initial = ""
        self.error_msg_initial = error_msg
        self.error_label = None
        self.verify_handler = verify_handler
        self.attempt_count = 0
        self.max_attempts = 5
        self.verify_history = []

    def get_current_state(self):
        """Returns the current input state (account and password)."""
        return {
            "account": self.account_entry.get().strip() if self.account_entry else "",
            "password": self.password_entry.get() if self.password_entry else ""
        }

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
                # If data is a dict (like credentials), we don't want to overwrite it with history string 
                # unless we add a specific field.
                elif isinstance(data, dict):
                    data["history"] = history_str
            
            super().finalize(status, data, reason=reason)

    def on_submit(self):
        """Validates input and processes the login."""
        state = self.get_current_state()
        if not all(state.values()):
            error_msg = self._("login_error_empty", "Please enter both credentials.")
            self.show_error(error_msg)
            return
            
        # UI Feedback: Disable button and show logging in state
        self.set_loading(True)
        
        if self.verify_handler:
            # Execute verification handler in a separate thread to keep UI responsive
            def do_verify():
                self.attempt_count += 1
                try:
                    res = self.verify_handler(state)
                    if res.get("status") == "success":
                        self.callback_queue.put(lambda: self.finalize("success", res.get("data", state)))
                    else:
                        err = res.get("message", "Unknown error")
                        self.verify_history.append({"idx": self.attempt_count, "error": err})
                        self.callback_queue.put(lambda: self.handle_verify_fail(err))
                except Exception as e:
                    err = str(e)
                    self.verify_history.append({"idx": self.attempt_count, "error": err})
                    self.callback_queue.put(lambda: self.handle_verify_fail(err))

            threading.Thread(target=do_verify, daemon=True).start()
        else:
            # Legacy mode: close and return to parent for verification
            self.root.after(100, lambda: self.finalize("success", state))

    def set_loading(self, is_loading: bool):
        """Toggle loading state in UI."""
        self.timer_frozen = is_loading
        if is_loading:
            if self.submit_btn:
                self.submit_btn.config(state="disabled", text=self._("btn_logging_in", "Logging In ..."))
            if self.cancel_btn: self.cancel_btn.pack_forget()
            if self.add_time_btn: self.add_time_btn.pack_forget()
            self.set_inputs_locked(True)
        else:
            if self.submit_btn:
                self.submit_btn.config(state="normal", text=self._("btn_login", "Login"))
            # Restore buttons in original order (packing right-to-left)
            # Submit is already there. Next should be Add Time, then Cancel.
            if self.add_time_btn:
                self.add_time_btn.pack(side="right", padx=(0, 10))
            if self.cancel_btn: 
                self.cancel_btn.pack(side="right", padx=(0, 10))
            self.set_inputs_locked(False)

    def set_inputs_locked(self, locked: bool):
        """Lock/Unlock input fields."""
        state = "disabled" if locked else "normal"
        if self.account_entry: self.account_entry.config(state=state)
        if self.password_entry: self.password_entry.config(state=state)
        if hasattr(self, 'pw_toggle_btn') and self.pw_toggle_btn:
            self.pw_toggle_btn.config(state=state)

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

    def show_error(self, message: str):
        """Display error message in the UI."""
        if self.error_label:
            self.error_label.config(text=message)
        else:
            self.status_label.config(text=message, fg=get_gui_colors()["red"])

    def setup_ui(self):
        """Builds the Account/Password login interface."""
        import tkinter as tk
        self.root.geometry("700x400")
        
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
        
        if self.account_initial:
            self.account_entry.insert(0, self.account_initial)
            if self.lock_account:
                self.account_entry.config(state="readonly")
                self.password_entry_focus = True
            else:
                self.password_entry_focus = True
        else:
            self.password_entry_focus = False
            if not self.lock_account:
                self.account_entry.focus_set()

        # Password input (masked) with visibility toggle
        pw_lbl_text = self.password_label or self._("label_password", "Password:")
        tk.Label(main_frame, text=pw_lbl_text, font=get_label_style()).pack(anchor='w', pady=(0, 2))
        
        pw_container = tk.Frame(main_frame)
        pw_container.pack(fill=tk.X, pady=(0, 10))
        
        self.password_entry = tk.Entry(pw_container, font=get_label_style(), show="*")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Visibility toggle button
        self.pw_visible = False
        def toggle_pw():
            self.pw_visible = not self.pw_visible
            self.password_entry.config(show="" if self.pw_visible else "*")
            self.pw_toggle_btn.config(text="👁" if not self.pw_visible else "🙈")
            
        self.pw_toggle_btn = tk.Button(pw_container, text="👁", command=toggle_pw, 
                                       font=("Arial", 12), width=3, relief="flat", borderwidth=0)
        self.pw_toggle_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Error message display (below password)
        from logic._.gui.tkinter.style import get_secondary_label_style
        self.error_label = tk.Label(main_frame, text="", font=get_secondary_label_style(), 
                                    fg=get_gui_colors()["red"], wraplength=350, justify="left")
        self.error_label.pack(fill=tk.X, pady=(0, 5))
        if self.error_msg_initial:
            self.error_label.config(text=self.error_msg_initial)
        
        if getattr(self, 'password_entry_focus', False):
            self.password_entry.focus_set()

        # Bindings
        self.root.bind('<Return>', lambda e: self.on_submit())
        
        # Start timer and focus
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)
