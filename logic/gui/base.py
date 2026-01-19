import tkinter as tk
import signal
import sys
import json
import time
import threading
import platform
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    from logic.gui.style import get_label_style, get_button_style, get_status_style, get_gui_colors
    from logic.lang.utils import get_translation
except ImportError:
    # Fallbacks for standalone execution
    def get_label_style(): return ("Arial", 10)
    def get_button_style(primary=False): return ("Arial", 10, "bold" if primary else "normal")
    def get_status_style(): return ("Arial", 11)
    def get_gui_colors(): return {"blue": "#007AFF", "green": "#28A745", "red": "#DC3545", "pulse": "#004085"}
    def get_translation(d, k, default): return default

class BaseGUIWindow:
    """
    Blueprint for Tool GUIs with timeout, signal handling, and state management.
    """
    def __init__(self, title: str, timeout: int, internal_dir: str):
        self.title = title
        self.remaining_time = timeout
        self.internal_dir = internal_dir
        self.root = None
        self.window_closed = False
        self.result = {"status": "error", "data": None}
        self.pulse_active = False # Flag to avoid timer overwriting pulse status
        
        # Signal registration
        signal.signal(signal.SIGINT, self.handle_external_signal)
        signal.signal(signal.SIGTERM, self.handle_external_signal)

    def _(self, key: str, default: str, **kwargs) -> str:
        return get_translation(self.internal_dir, key, default).format(**kwargs)

    def handle_external_signal(self, signum, frame):
        """Gracefully close on external signals, capturing current state."""
        if not self.window_closed:
            self.finalize("terminated", self.get_current_state())
            # Explicitly exit with signal-indicative code to help parent process
            # detect termination even if stdout capture fails.
            sys.exit(128 + signum)

    def check_signals(self):
        """Periodic check to allow Python to process signals."""
        if not self.window_closed and self.root:
            try: self.root.after(500, self.check_signals)
            except: pass

    def start_timer(self, status_label: tk.Label):
        """Standardized countdown timer."""
        if self.window_closed: return
        
        if not self.pulse_active:
            try:
                rem_msg = self._('time_remaining', 'Remaining:')
                status_label.config(text=f"{rem_msg} {self.remaining_time}s")
            except: pass
        
        if self.remaining_time > 0:
            self.remaining_time -= 1
            if self.root:
                self.root.after(1000, lambda: self.start_timer(status_label))
        else:
            self.finalize("timeout", self.get_current_state())

    def finalize(self, status: str, data: Any):
        """Unified closure point. status: success, cancelled, timeout, terminated, error."""
        if not self.window_closed:
            self.window_closed = True
            self.result = {"status": status, "data": data}
            try:
                # If terminated by signal, we want to make sure we print and exit
                if status == "terminated":
                    print("GDS_GUI_RESULT_JSON:" + json.dumps(self.result), flush=True)
                    time.sleep(0.1) # Small delay to ensure stdout is flushed
                if self.root: self.root.destroy()
            except: pass

    def get_current_state(self) -> Any:
        """Subclasses MUST override this to return their current state (input content, selections, etc.)."""
        return None

    def run(self, setup_func: Callable):
        """Main execution flow."""
        try:
            if platform.system() == "Darwin":
                # Try to use a class name for better dock/menu integration
                self.root = tk.Tk(className=self.__class__.__name__)
            else:
                self.root = tk.Tk()
            
            self.root.title(self.title)
            
            # Subclass-specific UI setup
            setup_func()
            
            # Start signal checking loop
            self.check_signals()
            
            self.root.protocol("WM_DELETE_WINDOW", lambda: self.finalize("cancelled", self.get_current_state()))
            self.root.mainloop()
            
            # Print final result for parent process to capture
            print("GDS_GUI_RESULT_JSON:" + json.dumps(self.result), flush=True)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.result = {"status": "error", "data": str(e)}
            print("GDS_GUI_RESULT_JSON:" + json.dumps(self.result), flush=True)

def setup_common_bottom_bar(parent, window_instance: BaseGUIWindow, 
                            submit_text: str, submit_cmd: Callable,
                            add_time_increment: int = 60) -> tk.Label:
    """
    Creates a standardized bottom bar with status, countdown, and buttons.
    """
    bottom_frame = tk.Frame(parent)
    # Restore minimal padding matching previous USERINPUT style
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=(0, 5))
    
    # Status label (left)
    status_label = tk.Label(bottom_frame, text="", font=get_status_style())
    status_label.pack(side=tk.LEFT)
    
    # Primary Button (right)
    tk.Button(bottom_frame, text=submit_text, command=submit_cmd, 
              font=get_button_style(primary=True)).pack(side=tk.RIGHT)
    
    # Add Time Button (right)
    if add_time_increment > 0:
        add_msg = window_instance._("add_time", "Add {seconds}s", seconds=add_time_increment)
        def on_add_time():
            window_instance.remaining_time += add_time_increment
            window_instance.pulse_active = True
            added_msg = window_instance._("time_added", "Time added!")
            status_label.config(text=f"{added_msg} {window_instance.remaining_time}s", fg=get_gui_colors()["pulse"])
            
            def reset_pulse():
                if not window_instance.window_closed:
                    window_instance.pulse_active = False
                    status_label.config(fg="black")
            
            window_instance.root.after(2000, reset_pulse)
            
        tk.Button(bottom_frame, text=add_msg, command=on_add_time, 
                  font=get_button_style()).pack(side=tk.RIGHT, padx=(0, 10))
    
    # Cancel Button (right)
    tk.Button(bottom_frame, text=window_instance._("btn_cancel", "Cancel"), 
              command=lambda: window_instance.finalize("cancelled", window_instance.get_current_state()), 
              font=get_button_style()).pack(side=tk.RIGHT, padx=(0, 10))
    
    return status_label

