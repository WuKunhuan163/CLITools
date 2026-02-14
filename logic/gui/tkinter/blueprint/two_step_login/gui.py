import sys
from pathlib import Path
import threading
from typing import Any, Optional, Callable, Dict

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/two_step_login/gui.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors, get_button_style

class TwoStepLoginWindow(BaseGUIWindow):
    """
    Blueprint for Two-Step Login (Account first, then Password if needed).
    Step 1: Account entry. 'Next' calls verify_handler.
    Step 2: Password entry. Account is locked. 'Prev' goes back.
    """
    def __init__(self, title, timeout, internal_dir, tool_name=None, 
                 instruction_text=None, account_label=None, password_label=None,
                 prompt_msg=None, error_msg=None, verify_handler: Optional[Callable[[Dict[str, str]], Dict[str, Any]]] = None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "LOGIN")
        self.instruction_text = instruction_text
        self.account_label_text = account_label
        self.password_label_text = password_label
        
        self.account_initial = ""
        self.prompt_msg_initial = prompt_msg
        self.error_msg_initial = error_msg
        self.verify_handler = verify_handler
        
        self.step = "account" # "account" or "password"
        self.attempt_count = 0
        self.max_attempts = 5
        self.verify_history = []
        
        # UI Elements
        self.main_frame = None
        self.fields_frame = None
        self.password_frame = None
        self.prev_btn = None
        self.account_entry = None
        self.password_entry = None
        self.error_label = None
        self.pw_toggle_btn = None

    def get_current_state(self):
        """Returns the current input state."""
        return {
            "account": self.account_entry.get().strip() if self.account_entry else "",
            "password": self.password_entry.get() if self.password_entry else "",
            "step": self.step
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
                elif isinstance(data, dict):
                    data["history"] = history_str
            
            super().finalize(status, data, reason=reason)

    def on_submit(self):
        """Validates input and processes the next step or login."""
        state = self.get_current_state()
        if self.step == "account":
            if not state["account"]:
                self.show_error(self._("login_error_empty_account", "Please enter your account."))
                return
        else:
            if not state["password"]:
                self.show_error(self._("login_error_empty_password", "Please enter your password."))
                return

        # UI Feedback
        self.set_loading(True)
        
        if self.verify_handler:
            # Execute verification handler in a separate thread
            def do_verify():
                self.attempt_count += 1
                try:
                    res = self.verify_handler(state)
                    if res.get("status") == "success":
                        self.callback_queue.put(lambda: self.finalize("success", res.get("data", state)))
                    elif res.get("status") == "need_password":
                        # Transitions to password step on main thread
                        self.callback_queue.put(self.go_to_password_step)
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
            # Legacy/Fallback mode
            if self.step == "account":
                self.go_to_password_step()
            else:
                self.finalize("success", state)

    def go_to_password_step(self):
        """Transition UI to password entry step."""
        self.set_loading(False)
        self.step = "password"
        self.account_entry.config(state="disabled")
        
        # Inside fields_frame, so it appears after account but before error_label
        self.password_frame.pack(fill="x", pady=(0, 10))
        self.password_entry.focus_set()
        
        if self.submit_btn:
            self.submit_btn.config(text=self._("btn_login", "Login"))
        # Show Prev button
        if self.prev_btn:
            self.prev_btn.pack(side="right", padx=(0, 10))
        self.show_error("", reset_color=True) # Clear any previous errors

    def go_to_account_step(self):
        """Transition UI back to account entry step."""
        self.step = "account"
        self.account_entry.config(state="normal")
        self.account_entry.focus_set()
        self.password_frame.pack_forget()
        if self.submit_btn:
            self.submit_btn.config(text=self._("btn_next", "Next"))
        if self.prev_btn:
            self.prev_btn.pack_forget()
        self.show_error("", reset_color=True)

    def set_loading(self, is_loading: bool):
        """Toggle loading state in UI."""
        self.timer_frozen = is_loading
        loading_text = self._("btn_verifying", "Verifying ...") if self.step == "account" else self._("btn_logging_in", "Logging In ...")
        
        if is_loading:
            if self.submit_btn:
                self.submit_btn.config(state="disabled", text=loading_text)
            if self.cancel_btn: self.cancel_btn.pack_forget()
            if self.add_time_btn: self.add_time_btn.pack_forget()
            if self.prev_btn: self.prev_btn.pack_forget()
            self.set_inputs_locked(True)
        else:
            submit_text = self._("btn_next", "Next") if self.step == "account" else self._("btn_login", "Login")
            if self.submit_btn:
                self.submit_btn.config(state="normal", text=submit_text)
            
            # Restore buttons in original order (packing right-to-left)
            if self.add_time_btn:
                self.add_time_btn.pack(side="right", padx=(0, 10))
            if self.cancel_btn: 
                self.cancel_btn.pack(side="right", padx=(0, 10))
            if self.step == "password" and self.prev_btn:
                self.prev_btn.pack(side="right", padx=(0, 10))
            self.set_inputs_locked(False)

    def set_inputs_locked(self, locked: bool):
        """Lock/Unlock input fields."""
        state = "disabled" if locked else "normal"
        # Account is always locked in password step
        if self.step == "account":
            if self.account_entry: self.account_entry.config(state=state)
        else:
            if self.account_entry: self.account_entry.config(state="disabled")
            
        if self.password_entry: self.password_entry.config(state=state)
        if self.pw_toggle_btn: self.pw_toggle_btn.config(state=state)

    def handle_verify_fail(self, error_msg: str):
        """Handle verification failure."""
        self.set_loading(False)
        full_error = f"Attempt {self.attempt_count}/{self.max_attempts}: {error_msg}"
        self.show_error(full_error)
        
        if self.attempt_count >= self.max_attempts:
            # Record history and exit
            history_str = "\n".join([f"Attempt {h['idx']}: {h['error']}" for h in self.verify_history])
            self.finalize("error", history_str, reason="max_attempts_exceeded")

    def show_error(self, message: str, reset_color: bool = False):
        """Display error message in the UI."""
        fg = "black" if reset_color else get_gui_colors()["red"]
        if self.error_label:
            self.error_label.config(text=message, fg=fg)
        else:
            self.status_label.config(text=message, fg=fg)

    def setup_ui(self):
        """Builds the two-step login interface."""
        import tkinter as tk
        self.root.geometry("700x400")
        
        # Initialize bottom bar from timed_bottom_bar
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_next", "Next"),
            submit_cmd=self.on_submit
        )
        
        # Add Prev button to bottom bar (managed by setup_ui)
        bb_frame = self.bottom_bar_frame
        self.prev_btn = tk.Button(bb_frame, text=self._("btn_prev", "Prev"), 
                                  command=self.go_to_account_step, font=get_button_style())
        # Initially hidden (don't pack yet)
        
        self.main_frame = tk.Frame(self.root, padx=25, pady=25)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Header
        instr = self.instruction_text or self._("login_instruction", "Please sign in")
        tk.Label(self.main_frame, text=instr, font=("Arial", 14, "bold")).pack(pady=(0, 20))

        # Fields frame (to contain account and password sections)
        self.fields_frame = tk.Frame(self.main_frame)
        self.fields_frame.pack(fill=tk.X)

        # Account Section (packed into fields_frame)
        acc_lbl_text = self.account_label_text or self._("label_account", "Account:")
        tk.Label(self.fields_frame, text=acc_lbl_text, font=get_label_style()).pack(anchor='w', pady=(0, 2))
        self.account_entry = tk.Entry(self.fields_frame, font=get_label_style())
        self.account_entry.pack(fill=tk.X, pady=(0, 15))
        if self.account_initial:
            self.account_entry.insert(0, self.account_initial)
        self.account_entry.focus_set()

        # Password Section (inside fields_frame, initially hidden)
        self.password_frame = tk.Frame(self.fields_frame)
        pw_lbl_text = self.password_label_text or self._("label_password", "Password:")
        tk.Label(self.password_frame, text=pw_lbl_text, font=get_label_style()).pack(anchor='w', pady=(0, 2))
        
        pw_container = tk.Frame(self.password_frame)
        pw_container.pack(fill=tk.X)
        self.password_entry = tk.Entry(pw_container, font=get_label_style(), show="*")
        self.password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.pw_visible = False
        def toggle_pw():
            self.pw_visible = not self.pw_visible
            self.password_entry.config(show="" if self.pw_visible else "*")
            self.pw_toggle_btn.config(text="👁" if not self.pw_visible else "🙈")
        self.pw_toggle_btn = tk.Button(pw_container, text="👁", command=toggle_pw, 
                                       font=("Arial", 12), width=3, relief="flat", borderwidth=0)
        self.pw_toggle_btn.pack(side=tk.RIGHT, padx=(5, 0))

        # Error label (packed into main_frame, AFTER fields_frame)
        from logic.gui.tkinter.style import get_secondary_label_style
        self.error_label = tk.Label(self.main_frame, text="", font=get_secondary_label_style(), 
                                    fg=get_gui_colors()["red"], wraplength=350, justify="left")
        self.error_label.pack(fill=tk.X, pady=(10, 5))
        if self.prompt_msg_initial:
            self.error_label.config(text=self.prompt_msg_initial, fg="black")
        elif self.error_msg_initial:
            self.error_label.config(text=self.error_msg_initial)

        # Bindings
        self.root.bind('<Return>', lambda e: self.on_submit())
        
        # Start timer and focus
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)
