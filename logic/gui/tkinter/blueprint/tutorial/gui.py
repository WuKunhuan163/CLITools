import sys
import os
import tkinter as tk
from pathlib import Path
from typing import Any, List, Optional, Callable, Dict, Union

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/tutorial/gui.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors, get_button_style

class TutorialStep:
    """Defines a single step in the tutorial."""
    def __init__(self, title: str, 
                 content_func: Callable[[tk.Frame, 'TutorialWindow'], None], 
                 validate_func: Optional[Callable[[], bool]] = None):
        self.title = title
        self.content_func = content_func # function(frame, window) to build UI
        self.validate_func = validate_func # returns True if step is complete

class TutorialWindow(BaseGUIWindow):
    """
    Blueprint for a multi-step tutorial or wizard.
    Left-top: Step a/b
    Middle: Content Container
    Bottom: Prev, Next/Complete
    """
    def __init__(self, title, timeout, internal_dir, steps: List[TutorialStep], tool_name=None):
        super().__init__(title, timeout, internal_dir, tool_name=tool_name or "TUTORIAL")
        self.steps = steps
        self.current_step_idx = 0
        
        # UI Elements
        self.step_indicator = None
        self.content_frame = None
        self.prev_btn = None
        self.main_frame = None
        self.error_label = None

    def get_current_state(self):
        """Returns the current progress."""
        return {"current_step": self.current_step_idx, "total_steps": len(self.steps)}

    def on_prev(self):
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            self.update_step_ui()

    def on_submit(self):
        """Handles 'Next' or 'Complete' button click."""
        step = self.steps[self.current_step_idx]
        if step.validate_func:
            if not step.validate_func():
                # Validation failed - step content should show its own error, 
                # but we can provide a generic fallback if needed.
                return

        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            self.update_step_ui()
        else:
            self.finalize("success", self.get_current_state())

    def show_error(self, message: str, is_info: bool = False):
        """Standardized error/info display for steps."""
        color = "black" if is_info else get_gui_colors()["red"]
        if self.error_label:
            self.error_label.config(text=message, fg=color)
        else:
            self.status_label.config(text=message, fg=color)

    def update_step_ui(self):
        """Clears and rebuilds the central content area for the current step."""
        if self.content_frame:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
        step = self.steps[self.current_step_idx]
        
        # 1. Update Step Indicator
        if self.step_indicator:
            text = self._("tutorial_step_count", "Step {current}/{total}", 
                          current=self.current_step_idx + 1, total=len(self.steps))
            self.step_indicator.config(text=text)
        
        # 2. Build Content
        step.content_func(self.content_frame, self)
        
        # 3. Update Buttons
        if self.prev_btn:
            if self.current_step_idx > 0:
                self.prev_btn.pack(side=tk.RIGHT, padx=(0, 10))
            else:
                self.prev_btn.pack_forget()
                
        if self.submit_btn:
            if self.current_step_idx == len(self.steps) - 1:
                btn_text = self._("btn_complete", "Complete")
            else:
                btn_text = self._("btn_next", "Next")
            self.submit_btn.config(text=btn_text)
            
        # 4. Clear any previous errors
        self.show_error("", is_info=True)

    def setup_ui(self):
        """Builds the shell of the tutorial window."""
        self.root.geometry("700x450")
        
        # Initialize bottom bar from base.py
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_next", "Next"),
            submit_cmd=self.on_submit
        )
        
        # Add Prev button to bottom bar (managed by us)
        bb_frame = self.bottom_bar_frame
        self.prev_btn = tk.Button(bb_frame, text=self._("btn_prev", "Prev"), 
                                  command=self.on_prev, font=get_button_style())
        
        # Main shell
        self.main_frame = tk.Frame(self.root, padx=25, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar: Step Indicator and Step Title
        top_frame = tk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.step_indicator = tk.Label(top_frame, text="", font=get_label_style(), fg="#666")
        self.step_indicator.pack(side=tk.LEFT)
        
        # Content Container
        self.content_frame = tk.Frame(self.main_frame)
        self.content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Optional Error Area at the bottom of content
        from logic.gui.tkinter.style import get_secondary_label_style
        self.error_label = tk.Label(self.main_frame, text="", font=get_secondary_label_style(), 
                                    fg=get_gui_colors()["red"], wraplength=600, justify="center")
        self.error_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        
        # Initial step
        self.update_step_ui()
        
        # Standard behaviors
        self.start_timer(self.status_label)
        self.root.lift()
        self.root.attributes("-topmost", True)

