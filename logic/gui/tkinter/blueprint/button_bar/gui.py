import tkinter as tk
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from logic.gui.tkinter.blueprint.base import BaseGUIWindow
from logic.gui.tkinter.style import get_label_style

class ButtonBarWindow(BaseGUIWindow):
    """
    A GUI blueprint that displays a horizontal row of buttons.
    Each button can have its own text, command, and optional style parameters.
    """
    def __init__(self, title: str, timeout: int, internal_dir: str, 
                 buttons: List[Dict[str, Any]], 
                 instruction: Optional[str] = None,
                 window_size: str = "500x120",
                 on_startup: Optional[Callable] = None,
                 focus_interval: int = 45):
        """
        Args:
            title: Window title.
            timeout: Auto-close timeout in seconds.
            internal_dir: Directory for localization files.
            buttons: List of dicts: {"text": str, "cmd": callable, "bg": str, "fg": str, "font": tuple, "close_on_click": bool}
            instruction: Optional text to display above buttons.
            window_size: Tkinter geometry string.
            on_startup: Callback executed after UI setup but before mainloop.
            focus_interval: Seconds between periodic focus/bell prompts.
        """
        super().__init__(title, timeout, internal_dir, focus_interval=focus_interval)
        self.buttons_config = buttons
        self.instruction_text = instruction
        self.window_size = window_size
        self.on_startup_callback = on_startup

    def setup_ui(self):
        from logic.gui.tkinter.style import get_button_style, get_label_style, get_gui_colors
        self.root.geometry(self.window_size)
        self.root.resizable(True, True)
        
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Optional Instruction Area (using Text for markdown-like bolding)
        if self.instruction_text:
            line_count = self.instruction_text.count('\n') + 1
            display_height = min(max(line_count, 2), 10)
            needs_scroll = line_count > 10

            text_frame = tk.Frame(main_frame)
            text_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 15))

            text_widget = tk.Text(
                text_frame, 
                font=get_label_style(),
                wrap=tk.WORD,
                height=display_height,
                padx=0,
                pady=0,
                borderwidth=0,
                highlightthickness=0,
                bg=main_frame.cget("bg")
            )

            if needs_scroll:
                scrollbar = tk.Scrollbar(text_frame, command=text_widget.yview)
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                text_widget.config(yscrollcommand=scrollbar.set)

            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            
            # Configure bold tag
            bold_font = list(get_label_style())
            if len(bold_font) >= 2:
                if len(bold_font) > 2:
                    bold_font[2] = "bold"
                else:
                    bold_font.append("bold")
            text_widget.tag_configure("bold", font=tuple(bold_font))
            
            # Simple bold parser (**text**)
            import re
            parts = re.split(r'(\*\*.*?\*\*)', self.instruction_text)
            for part in parts:
                if part.startswith("**") and part.endswith("**"):
                    text_widget.insert(tk.END, part[2:-2], "bold")
                else:
                    text_widget.insert(tk.END, part)
            
            text_widget.config(state=tk.DISABLED)

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True)
        
        delayed_buttons = []
        
        for i, btn_cfg in enumerate(self.buttons_config):
            text = btn_cfg.get("text", f"Button {i}")
            cmd = btn_cfg.get("cmd")
            close_on_click = btn_cfg.get("close_on_click", False)
            on_click_callback = btn_cfg.get("on_click")
            disable_seconds = btn_cfg.get("disable_seconds", 0)
            
            bg = btn_cfg.get("bg")
            fg = btn_cfg.get("fg")
            font = btn_cfg.get("font") or get_button_style()
            relief = btn_cfg.get("relief")
            bd = btn_cfg.get("bd")
            
            def create_cmd(actual_cmd, should_close, btn_ref_list, callback, btn_text=text):
                def wrapper():
                    if callback and btn_ref_list:
                        callback(btn_ref_list[0])
                    if actual_cmd:
                        actual_cmd()
                    if should_close:
                        self.finalize("success", btn_text)
                return wrapper

            btn_kwargs = {
                "text": text,
                "font": font
            }
            if bg: btn_kwargs["bg"] = bg
            if fg: btn_kwargs["fg"] = fg
            if relief: btn_kwargs["relief"] = relief
            if bd is not None: btn_kwargs["bd"] = bd

            btn_ref = []
            btn = tk.Button(button_frame, **btn_kwargs)
            btn_ref.append(btn)
            btn.config(command=create_cmd(cmd, close_on_click, btn_ref, on_click_callback))
            btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5 if i > 0 else 0, 0))

            if disable_seconds > 0:
                delayed_buttons.append((btn, text, disable_seconds))

        # Countdown-disable buttons that have disable_seconds
        for btn, original_text, seconds in delayed_buttons:
            btn.config(state="disabled", text=f"{original_text} ({seconds}s)")
            def countdown(b=btn, t=original_text, remaining=seconds):
                if remaining <= 1:
                    b.config(state="normal", text=t)
                    return
                b.config(text=f"{t} ({remaining - 1}s)")
                self.root.after(1000, lambda: countdown(b, t, remaining - 1))
            self.root.after(1000, lambda b=btn, t=original_text, s=seconds: countdown(b, t, s))

        if self.on_startup_callback:
            self.root.after(100, self.on_startup_callback)

    def run(self, custom_id: Optional[str] = None):
        super().run(self.setup_ui, custom_id=custom_id)

