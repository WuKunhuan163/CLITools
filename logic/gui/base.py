import tkinter as tk
import signal
import sys
import json
import time
import threading
import platform
import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any, Callable

try:
    from logic.gui.style import get_label_style, get_button_style, get_status_style, get_gui_colors, get_secondary_label_style
    from logic.lang.utils import get_translation
except ImportError:
    # Fallbacks for standalone execution
    def get_label_style(): return ("Arial", 10)
    def get_secondary_label_style(): return ("Arial", 9, "italic")
    def get_button_style(primary=False): return ("Arial", 10, "bold" if primary else "normal")
    def get_status_style(): return ("Arial", 11)
    def get_gui_colors(): return {"blue": "#007AFF", "green": "#28A745", "red": "#DC3545", "pulse": "#004085"}
    def get_translation(d, k, default): return default

class BaseGUIWindow:
    """
    Blueprint for Tool GUIs with timeout, signal handling, and state management.
    """
    def __init__(self, title: str, timeout: int, internal_dir: str, tool_name: str = None):
        self.title = title
        self.remaining_time = timeout
        self.internal_dir = internal_dir
        self.tool_name = tool_name
        self.root = None
        self.window_closed = False
        self.result = {"status": "error", "data": None}
        self.pulse_active = False # Flag to avoid timer overwriting pulse status
        
        # Signal registration
        signal.signal(signal.SIGINT, self.handle_external_signal)
        signal.signal(signal.SIGTERM, self.handle_external_signal)

    def _(self, key: str, default: str, **kwargs) -> str:
        # 1. Try tool-specific translation
        val = get_translation(self.internal_dir, key, None)
        if val is None:
            # 2. Try shared GUI component translation
            gui_logic_dir = str(Path(__file__).resolve().parent)
            val = get_translation(gui_logic_dir, key, default)
        return val.format(**kwargs)

    def handle_external_signal(self, signum, frame):
        """Gracefully close on external signals, capturing current state."""
        if not self.window_closed:
            # Check if it was a real remote stop or just a random signal
            project_root = Path(self.internal_dir).parent.parent.parent
            stop_file = project_root / "data" / "run" / "stops" / f"{os.getpid()}.stop"
            is_remote_stop = stop_file.exists()
            
            self.finalize("terminated", self.get_current_state())
            
            # Print result before exiting from signal handler
            print("GDS_GUI_RESULT_JSON:" + json.dumps(self.result), flush=True)
            
            sys.exit(128 + signum)

    def check_signals(self):
        """Periodic check to allow Python to process signals and check for stop flags."""
        if not self.window_closed and self.root:
            # Check project root for data/run/stops/
            try:
                project_root = Path(self.internal_dir).parent.parent.parent
                stops_dir = project_root / "data" / "run" / "stops"
                
                # Detect flags for this PID
                pid = os.getpid()
                
                # 1. STOP flag (Original mechanism)
                stop_file = stops_dir / f"{pid}.stop"
                if stop_file.exists():
                    stop_file.unlink()
                    self.finalize("terminated", self.get_current_state())
                    return

                # 2. SUBMIT flag
                submit_file = stops_dir / f"{pid}.submit"
                if submit_file.exists():
                    submit_file.unlink()
                    self.finalize("success", self.get_current_state())
                    return

                # 3. CANCEL flag
                cancel_file = stops_dir / f"{pid}.cancel"
                if cancel_file.exists():
                    cancel_file.unlink()
                    self.finalize("cancelled", self.get_current_state())
                    return

                # 4. ADD_TIME flag
                add_time_file = stops_dir / f"{pid}.add_time"
                if add_time_file.exists():
                    add_time_file.unlink()
                    # Trigger the add_time pulse if possible
                    if hasattr(self, "on_remote_add_time"):
                        self.on_remote_add_time()
            except Exception:
                pass

            # Schedule next check
            try: self.root.after(500, self.check_signals)
            except: pass

    def start_timer(self, status_label: tk.Label):
        """Standardized countdown timer."""
        if self.window_closed: return
        
        # Save default color if not already saved
        if not hasattr(self, '_default_status_fg'):
            self._default_status_fg = status_label.cget("fg")

        if not self.pulse_active:
            try:
                rem_msg = self._('time_remaining', 'Remaining:')
                status_label.config(text=f"{rem_msg} {self.remaining_time}s", fg=self._default_status_fg)
            except: pass
        
        if self.remaining_time > 0:
            self.remaining_time -= 1
            if self.root:
                self.root.after(1000, lambda: self.start_timer(status_label))
        else:
            # Capture State A and return via Interface I
            self.finalize("timeout", self.get_current_state())

    def finalize(self, status: str, data: Any):
        """Unified closure point (Interface I). status: success, cancelled, timeout, terminated, error."""
        if not self.window_closed:
            self.window_closed = True
            self.result = {"status": status, "data": data}
            try:
                if self.root: self.root.destroy()
            except: pass

    def get_current_state(self) -> Any:
        """Subclasses MUST override this to return their current state (State A)."""
        return None

    def run(self, setup_func: Callable, on_show: Optional[Callable] = None, custom_id: Optional[str] = None):
        """Main execution flow."""
        try:
            if platform.system() == "Darwin":
                self.root = tk.Tk(className=self.__class__.__name__)
            else:
                self.root = tk.Tk()
            
            self.root.title(self.title)
            setup_func()
            
            # 1. Register instance for registry-based stop
            try:
                project_root = Path(self.internal_dir).parent.parent.parent
                instance_dir = project_root / "data" / "run" / "instances"
                instance_dir.mkdir(parents=True, exist_ok=True)
                self.instance_file = instance_dir / f"gui_{os.getpid()}.json"
                with open(self.instance_file, "w") as f:
                    json.dump({
                        "pid": os.getpid(), 
                        "tool_name": self.tool_name,
                        "title": self.title, 
                        "custom_id": custom_id, # Added
                        "class": self.__class__.__name__,
                        "start_time": time.time()
                    }, f)
            except:
                self.instance_file = None

            self.check_signals()
            self.root.protocol("WM_DELETE_WINDOW", lambda: self.finalize("cancelled", self.get_current_state()))
            
            if on_show is not None:
                self.root.after(100, on_show)

            self.root.mainloop()
            
            # Cleanup stop files if they exist for this PID
            try:
                project_root = Path(self.internal_dir).parent.parent.parent
                stops_dir = project_root / "data" / "run" / "stops"
                pid = os.getpid()
                for ext in ["stop", "submit", "cancel", "add_time"]:
                    f = stops_dir / f"{pid}.{ext}"
                    if f.exists(): f.unlink()
            except: pass

            # Cleanup registry
            if hasattr(self, 'instance_file') and self.instance_file and self.instance_file.exists(): 
                try: self.instance_file.unlink()
                except: pass
                
            # Print final result for parent process to capture
            print("GDS_GUI_RESULT_JSON:" + json.dumps(self.result), flush=True)
        except Exception as e:
            if hasattr(self, 'instance_file') and self.instance_file and self.instance_file.exists():
                try: self.instance_file.unlink()
                except: pass
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
    # Standard padding matching USERINPUT style
    bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(5, 15))
    
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
            
            # Update label immediately to avoid flashing
            added_msg = window_instance._("time_added", "Time added!")
            status_label.config(text=f"{added_msg} {window_instance.remaining_time}s", fg=get_gui_colors()["pulse"])
            
            def reset_pulse():
                if not window_instance.window_closed:
                    window_instance.pulse_active = False
                    # Switch back to normal countdown text immediately
                    rem_msg = window_instance._('time_remaining', 'Remaining:')
                    status_label.config(text=f"{rem_msg} {window_instance.remaining_time}s", fg=window_instance._default_status_fg)
            
            window_instance.root.after(2000, reset_pulse)
        
        # Register for remote trigger
        window_instance.on_remote_add_time = on_add_time
            
        tk.Button(bottom_frame, text=add_msg, command=on_add_time, 
                  font=get_button_style()).pack(side=tk.RIGHT, padx=(0, 10))
    
    # Cancel Button (right)
    tk.Button(bottom_frame, text=window_instance._("btn_cancel", "Cancel"), 
              command=lambda: window_instance.finalize("cancelled", window_instance.get_current_state()), 
              font=get_button_style()).pack(side=tk.RIGHT, padx=(0, 10))
    
    return status_label
