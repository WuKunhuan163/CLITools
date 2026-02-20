import sys
import os
import tkinter as tk
import time
from pathlib import Path
from typing import Any, List, Optional, Callable, Dict, Union

# ... (other imports)
from logic.gui.tkinter.blueprint.base import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style, get_gui_colors, get_button_style

def log_tutorial(msg: str):
    """Utility to log tutorial operations for debugging."""
    try:
        log_path = Path("/Applications/AITerminalTools/tmp/tutorial_debug.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a") as f:
            f.write(f"[{time.strftime('%H:%M:%S')}] {msg}\n")
    except:
        pass

class TutorialStep:
    """Defines a single step in the tutorial."""
    def __init__(self, title: str, 
                 content_func: Callable[[tk.Frame, 'TutorialWindow'], None], 
                 validate_func: Optional[Callable[[], bool]] = None,
                 is_manual: bool = False):
        self.title = title
        self.content_func = content_func # function(frame, window) to build UI
        self.validate_func = validate_func # returns True if step is complete
        self.is_manual = is_manual

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
        
        # Validation state tracking
        self.step_validated_states = [False] * len(self.steps)
        
        # Persistent tutorial data (e.g. captured inputs)
        self.tutorial_data = {}
        
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
        log_tutorial(f"Setting step {self.current_step_idx} validated: {is_valid}")
        self.step_validated_states[self.current_step_idx] = is_valid
        if self.submit_btn:
            if is_valid:
                self.submit_btn.config(state=tk.NORMAL)
            else:
                self.submit_btn.config(state=tk.DISABLED)

    def get_current_state(self):
        """Returns the current progress."""
        return {"current_step": self.current_step_idx, "total_steps": len(self.steps)}

    def on_prev(self):
        log_tutorial(f"Prev clicked. Current index: {self.current_step_idx}")
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
            log_tutorial(f"New index after prev: {self.current_step_idx}")
            self.update_step_ui()

    def on_submit(self):
        """Handles 'Next' or 'Complete' button click."""
        log_tutorial(f"Submit clicked. Current index: {self.current_step_idx}")
        step = self.steps[self.current_step_idx]
        if step.validate_func:
            log_tutorial("Running step.validate_func")
            if not step.validate_func():
                log_tutorial("Validation failed")
                return
            log_tutorial("Validation success")

        if self.current_step_idx < len(self.steps) - 1:
            self.current_step_idx += 1
            log_tutorial(f"New index after submit (Next): {self.current_step_idx}")
            self.update_step_ui()
        else:
            log_tutorial("Finalizing tutorial (Complete)")
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
        log_tutorial(f"Updating Step UI. Index: {self.current_step_idx}, Total: {len(self.steps)}")
        if self.content_frame:
            for widget in self.content_frame.winfo_children():
                widget.destroy()
        
        # Reset block and image management for the new step
        self.blocks = []
        self.resizable_images = []
            
        step = self.steps[self.current_step_idx]
        log_tutorial(f"Building step: {step.title}")
        
        # 1. Update Step Indicator
        if self.step_indicator:
            text = self._("tutorial_step_count", "Step {current}/{total}", 
                          current=self.current_step_idx + 1, total=len(self.steps))
            self.step_indicator.config(text=text)
            log_tutorial(f"Indicator updated: {text}")
        
        # 2. Reset submit button state for new step
        # If the step has a validate_func, it must be validated by that function.
        # Otherwise, if it's manual, it must be validated via set_step_validated(True).
        # Otherwise (informational), it's validated by default.
        if step.validate_func is not None:
            is_valid = step.validate_func()
        elif step.is_manual:
            is_valid = self.step_validated_states[self.current_step_idx]
        else:
            # Informational steps are valid by default
            is_valid = True
            
        log_tutorial(f"Initial state for step {self.current_step_idx} (manual={step.is_manual}): {is_valid}")
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
            is_last = (self.current_step_idx == len(self.steps) - 1)
            log_tutorial(f"Setting submit button text. Is last: {is_last} (idx={self.current_step_idx}, len={len(self.steps)})")
            if is_last:
                btn_text = self._("btn_complete", "Complete")
            else:
                btn_text = self._("btn_next", "Next")
            self.submit_btn.config(text=btn_text)
            log_tutorial(f"Submit button text updated to: {btn_text}")
            
        # 5. Clear any previous errors
        self.show_error("", is_info=True)
        
        # 6. Final UI updates and scroll reset
        # Important: update_idletasks AFTER adding all content to ensure bbox is accurate
        self.root.update_idletasks()
        try:
            # Re-calculate scroll region based on actual content size
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            log_tutorial(f"Scrollregion updated: {self.canvas.bbox('all')}")
        except: pass
        
        self.canvas.yview_moveto(0)
        
        log_tutorial("Step UI update finished.")

    def bind_scroll_recursive(self, widget):
        """Recursively binds mousewheel to widgets to ensure they don't swallow events."""
        # Use our standard _on_mousewheel handler
        widget.bind("<MouseWheel>", self._on_mousewheel_event, add="+")
        widget.bind("<Button-4>", self._on_mousewheel_event, add="+")
        widget.bind("<Button-5>", self._on_mousewheel_event, add="+")
        
        for child in widget.winfo_children():
            self.bind_scroll_recursive(child)

    def _on_mousewheel_event(self, event):
        """Unified mousewheel handler for the tutorial window."""
        if not self.root or self.window_closed: return
        
        # Determine direction and magnitude
        delta = 0
        import platform
        if event.num == 4: delta = -3 # Linux scroll up
        elif event.num == 5: delta = 3 # Linux scroll down
        elif platform.system() == "Darwin":
            d = event.delta
            if abs(d) >= 120: d = d // 120
            delta = -3 * d
        else:
            delta = -1 * (event.delta // 120) * 3
        
        if delta != 0:
            try:
                log_tutorial(f"Scroll event captured from {event.widget} (delta={event.delta}, result={delta})")
                self.canvas.yview_scroll(delta, "units")
            except: pass
        
        # Returning "break" would stop propagation, but we might want it to propagate?
        # Actually, if we use bind_all, we don't need this recursive binding.
        # But if bind_all is failing, recursive binding is a fallback.
        # If we use both, we might get double scroll.
        # Let's try recursive binding ONLY for now and remove bind_all.

    def setup_ui(self):
        """Builds the shell of the tutorial window."""
        self.root.geometry("800x650") # Increased size for better image quality and visibility
        
        # Initialize bottom bar from base.py
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text=self._("btn_next", "Next"),
            submit_cmd=self.on_submit
        )
        
        # ... (button packing logic) ...
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
        
        self.canvas = tk.Canvas(container, highlightthickness=0, borderwidth=0)
        self.scrollbar = tk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, borderwidth=0, highlightthickness=0)
        
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
        
        # Robust mouse wheel support via bind_all
        def _on_mousewheel(event):
            if not self.root or self.window_closed: return
            delta = 0
            import platform
            if event.num == 4: delta = -3
            elif event.num == 5: delta = 3
            elif platform.system() == "Darwin":
                d = event.delta
                if abs(d) >= 120: d = d // 120
                delta = -3 * d
            else:
                delta = -1 * (event.delta // 120) * 3
            
            if delta != 0:
                log_tutorial(f"GLOBAL scroll event: {event.widget} delta={delta}")
                self.canvas.yview_scroll(delta, "units")
            return "break" # Prevent double scroll

        # Bind to everything
        self.root.bind_all("<MouseWheel>", _on_mousewheel)
        self.root.bind_all("<Button-4>", _on_mousewheel)
        self.root.bind_all("<Button-5>", _on_mousewheel)
        
        # Ensure focus for scroll events
        self.canvas.bind("<Enter>", lambda e: self.canvas.focus_set())
        
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

