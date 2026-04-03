"""
@export_module("gui.blueprint.tutorial.gui")
"""
"""[Internal]

"""
from src.core.io import turing_internal
import sys
import platform
import tkinter as tk
from pathlib import Path
from typing import Any, List, Optional, Callable

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.gui.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
from src.gui.style import get_label_style, get_gui_colors, get_button_style

_tutorial_log_path = None

@turing_internal
def log_tutorial(msg: str):
    """[Internal]
Writes debug messages to a tutorial session log file."""
    pass

class TutorialStep:
    """[Internal]
Defines a single step in the tutorial."""
    def __init__(self, title: str, 
                 content_func: Callable[[tk.Frame, 'TutorialWindow'], None], 
                 validate_func: Optional[Callable[[], bool]] = None):
        self.title = title
        self.content_func = content_func # function(frame, window) to build UI
        self.validate_func = validate_func # returns True if step is complete

class TutorialWindow(BaseGUIWindow):
    """[Internal]

    Blueprint for a multi-step tutorial or wizard.
    Left-top: Step a/b
    Middle: Content Container
    Bottom: Prev, Next/Complete
    """
    def __init__(self, title, timeout, internal_dir, steps: List[TutorialStep], tool_name=None,
                 on_step_change: Optional[Callable[[int, int, str], None]] = None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "TUTORIAL")
        self.steps = steps
        self.current_step_idx = 0
        self.project_root = None
        self.on_step_change = on_step_change
        
        self.step_indicator = None
        self.content_frame = None
        self.prev_btn = None
        self.main_frame = None
        self.error_label = None

        curr = Path(__file__).resolve().parent
        while curr != curr.parent:
            if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
                self.project_root = curr
                break
            curr = curr.parent

    @turing_internal
    def set_step_validated(self, is_valid: bool):
        """[Internal]
Enable or disable the submit button based on step validation."""
        if self.submit_btn:
            if is_valid:
                self.submit_btn.config(state=tk.NORMAL)
            else:
                self.submit_btn.config(state=tk.DISABLED)

    @turing_internal
    def get_current_state(self):
        """[Internal]
Returns the current progress."""
        return {"current_step": self.current_step_idx, "total_steps": len(self.steps)}

    @turing_internal
    def on_prev(self):
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            self.update_step_ui()

    @turing_internal
    def on_submit(self):
        """[Internal]
Handles 'Next' or 'Complete' button click."""
        step = self.steps[self.current_step_idx]
        if step.validate_func:
            if not step.validate_func():
                return

        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self.update_step_ui()
        else:
            self.finalize("success", self.get_current_state())

    @turing_internal
    def show_error(self, message: str, is_info: bool = False):
        """[Internal]
Standardized error/info display for steps."""
        color = "black" if is_info else get_gui_colors()["red"]
        if self.error_label:
            self.error_label.config(text=message, fg=color)
        else:
            self.status_label.config(text=message, fg=color)

    @turing_internal
    def update_step_ui(self):
        """[Internal]
Clears and rebuilds the central content area for the current step."""
        if self.content_frame:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
        
        self.blocks = []
        self.resizable_images = []
            
        step = self.steps[self.current_step_idx]
        
        if self.step_indicator:
            text = self._("tutorial_step_count", "Step {current}/{total}", 
                          current=self.current_step_idx + 1, total=len(self.steps))
            self.step_indicator.config(text=text)
        
        is_valid = (step.validate_func is None)
        self.set_step_validated(is_valid)
        
        step.content_func(self.content_frame, self)
        
        if self.submit_btn:
            self.submit_btn.pack_forget()
            self.submit_btn.pack(side=tk.RIGHT)
            
        if self.add_time_btn:
            self.add_time_btn.pack_forget()
            self.add_time_btn.pack(side=tk.RIGHT, padx=(0, 10))
            
        if self.prev_btn:
            self.prev_btn.pack_forget()
            if self.current_step_idx > 0:
                self.prev_btn.pack(side=tk.RIGHT, padx=(0, 10))
                
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
            self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
            
        if self.submit_btn:
            if self.current_step_idx == len(self.steps) - 1:
                btn_text = self._("btn_complete", "Complete")
            else:
                btn_text = self._("btn_next", "Next")
            self.submit_btn.config(text=btn_text)
            
        self.show_error("", is_info=True)

        if self.on_step_change:
            try:
                self.on_step_change(self.current_step_idx, len(self.steps), step.title)
            except Exception:
                pass

    @turing_internal
    def setup_ui(self):
        """[Internal]
Builds the shell of the tutorial window."""
        self.root.geometry("800x650") # Increased size for better image quality and visibility
        
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_next", "Next"),
            submit_cmd=self.on_submit
        )
        
        
        if self.submit_btn:
            self.submit_btn.pack_forget()
        if self.add_time_btn:
            self.add_time_btn.pack_forget()
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
            
        if self.submit_btn:
            self.submit_btn.pack(side=tk.RIGHT)
        if self.add_time_btn:
            self.add_time_btn.pack(side=tk.RIGHT, padx=(0, 10))
            
        bb_frame = self.bottom_bar_frame
        self.prev_btn = tk.Button(bb_frame, text=self._("btn_prev", "Prev"), 
                                  command=self.on_prev, font=get_button_style())
        
        if self.cancel_btn:
            self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        self.main_frame = tk.Frame(self.root, padx=25, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        top_frame = tk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.step_indicator = tk.Label(top_frame, text="", font=get_label_style(), fg="#666")
        self.step_indicator.pack(side=tk.LEFT)
        
        container = tk.Frame(self.main_frame)
        container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        @turing_internal
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        @turing_internal
        def _on_mousewheel(event):
            if platform.system() == "Darwin":
                self.canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.content_frame = self.scrollable_frame
        
        from src.gui.style import get_secondary_label_style as get_secondary_label_style
        self.error_label = tk.Label(self.main_frame, text="", font=get_secondary_label_style(), 
                                    fg=get_gui_colors()["red"], wraplength=600, justify="center")
        self.error_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        self.update_step_ui()
        
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)

    @turing_internal
    def finalize(self, status: str, data: Any, reason: Optional[str] = None):
        """[Internal]
Override to ensure a reason is set for cancelled."""
        if status == "cancelled" and not reason:
            reason = self._("tutorial_user_closed", "User closed tutorial")
        super().finalize(status, data, reason=reason)

    @turing_internal
    def add_clickable_url(self, frame, text, url):
        """[Internal]
Utility to add a clickable URL label."""
        import webbrowser
        link = tk.Label(frame, text=text, font=get_label_style(), fg="blue", cursor="hand2", wraplength=600)
        link.pack(pady=2)
        link.bind("<Button-1>", lambda e: webbrowser.open_new(url))
        return link

