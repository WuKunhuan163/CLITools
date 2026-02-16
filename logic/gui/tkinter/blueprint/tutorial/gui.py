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
        self.project_root = None # Will be set during find_root in subclasses or manually
        
        # UI Elements
        self.step_indicator = None
        self.content_frame = None
        self.prev_btn = None
        self.main_frame = None
        self.error_label = None

        # Find project root
        curr = Path(__file__).resolve().parent
        while curr != curr.parent:
            if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
                self.project_root = curr
                break
            curr = curr.parent

    def set_step_validated(self, is_valid: bool):
        """Enable or disable the submit button based on step validation."""
        if self.submit_btn:
            if is_valid:
                self.submit_btn.config(state=tk.NORMAL)
            else:
                self.submit_btn.config(state=tk.DISABLED)

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
        
        # Reset block and image management for the new step
        self.blocks = []
        self.resizable_images = []
            
        step = self.steps[self.current_step_idx]
        
        # 1. Update Step Indicator
        if self.step_indicator:
            text = self._("tutorial_step_count", "Step {current}/{total}", 
                          current=self.current_step_idx + 1, total=len(self.steps))
            self.step_indicator.config(text=text)
        
        # 2. Reset submit button state for new step
        # If the step has no validate_func, it's considered valid by default
        is_valid = (step.validate_func is None)
        self.set_step_validated(is_valid)
        
        # 3. Build Content
        step.content_func(self.content_frame, self)
        
        # 4. Update Buttons
        # Button Order: Cancel (L among buttons), Prev, Add 60s, Next (R)
        # Re-pack R-to-L: Next, Add 60s, Prev, Cancel
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
            
        # 5. Clear any previous errors
        self.show_error("", is_info=True)

    def add_inline_links(self, frame, text_content):
        """
        Creates a tk.Text widget that supports inline clickable links.
        Format: "Some text [Link Label](https://link.url) and more text."
        """
        import webbrowser
        import re
        
        text_widget = tk.Text(frame, wrap=tk.WORD, font=get_label_style(), 
                              padx=20, pady=10, borderwidth=0, highlightthickness=0,
                              bg=frame.cget("bg"), height=10) # Height will adjust
        text_widget.pack(fill=tk.X, expand=True)
        
        # Make it look like a label
        text_widget.config(state=tk.NORMAL)
        
        # Regex for [label](url)
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        last_idx = 0
        for match in re.finditer(pattern, text_content):
            # Normal text before link
            text_widget.insert(tk.END, text_content[last_idx:match.start()])
            
            # Link label
            label, url = match.groups()
            tag_name = f"link_{match.start()}"
            text_widget.insert(tk.END, label, tag_name)
            
            text_widget.tag_config(tag_name, foreground="blue", underline=True)
            text_widget.tag_bind(tag_name, "<Enter>", lambda e: text_widget.config(cursor="hand2"))
            text_widget.tag_bind(tag_name, "<Leave>", lambda e: text_widget.config(cursor="arrow"))
            text_widget.tag_bind(tag_name, "<Button-1>", lambda e, u=url: webbrowser.open_new(u))
            
            last_idx = match.end()
            
        # Remaining text
        text_widget.insert(tk.END, text_content[last_idx:])
        
        # Disable editing
        text_widget.config(state=tk.DISABLED)
        
        # Adjust height based on content
        num_lines = int(text_widget.index('end-1c').split('.')[0])
        text_widget.config(height=num_lines + 1)
        
        # Ensure it responds to resize if it's inside a block
        # (Though tk.Text handles wrapping natively, we might need to refresh height)
        def refresh_height(event):
            num_lines = int(text_widget.index('end-1c').split('.')[0])
            text_widget.config(height=num_lines + 1)
        text_widget.bind("<Configure>", refresh_height)
        
        return text_widget

    def setup_ui(self):
        """Builds the shell of the tutorial window."""
        self.root.geometry("800x650") # Increased size for better image quality and visibility
        
        # Initialize bottom bar from base.py
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_next", "Next"),
            submit_cmd=self.on_submit
        )
        
        # Button Order Adjustment: Cancel, Prev, Add 60s, Next
        # Currently packed in setup_common_bottom_bar: 
        # [Status (L)] ... [Cancel (R)] [Add 60s (R)] [Next (R)]
        # We need to re-pack them in the desired order: Cancel (Leftmost among buttons), Prev, Add 60s, Next (Rightmost)
        
        if self.submit_btn:
            self.submit_btn.pack_forget()
        if self.add_time_btn:
            self.add_time_btn.pack_forget()
        if self.cancel_btn:
            self.cancel_btn.pack_forget()
            
        # Re-pack everything tk.RIGHT in reverse requested order: 
        # Next (far right), Add 60s, Prev, Cancel
        if self.submit_btn:
            self.submit_btn.pack(side=tk.RIGHT)
        if self.add_time_btn:
            self.add_time_btn.pack(side=tk.RIGHT, padx=(0, 10))
            
        bb_frame = self.bottom_bar_frame
        self.prev_btn = tk.Button(bb_frame, text=self._("btn_prev", "Prev"), 
                                  command=self.on_prev, font=get_button_style())
        # self.prev_btn will be packed/unpacked in update_step_ui
        
        if self.cancel_btn:
            self.cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # Main shell
        self.main_frame = tk.Frame(self.root, padx=25, pady=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Top bar: Step Indicator
        top_frame = tk.Frame(self.main_frame)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.step_indicator = tk.Label(top_frame, text="", font=get_label_style(), fg="#666")
        self.step_indicator.pack(side=tk.LEFT)
        
        # Scrollable Content Container
        container = tk.Frame(self.main_frame)
        container.pack(fill=tk.BOTH, expand=True)
        
        self.canvas = tk.Canvas(container, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        # Create a window inside the canvas to hold our scrollable frame
        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Sync width of scrollable_frame to canvas width
        def on_canvas_configure(event):
            self.canvas.itemconfig(self.canvas_window, width=event.width)
        self.canvas.bind("<Configure>", on_canvas_configure)
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Mouse wheel support
        def _on_mousewheel(event):
            if platform.system() == "Darwin":
                self.canvas.yview_scroll(int(-1 * event.delta), "units")
            else:
                self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        self.content_frame = self.scrollable_frame
        
        # Optional Error Area at the bottom
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

    def finalize(self, status: str, data: Any, reason: Optional[str] = None):
        """Override to ensure a reason is set for cancelled."""
        if status == "cancelled" and not reason:
            reason = "User closed tutorial"
        super().finalize(status, data, reason=reason)

    def add_clickable_url(self, frame, text, url):
        """Utility to add a clickable URL label."""
        import webbrowser
        link = tk.Label(frame, text=text, font=get_label_style(), fg="blue", cursor="hand2", wraplength=600)
        link.pack(pady=2)
        link.bind("<Button-1>", lambda e: webbrowser.open_new(url))
        return link

