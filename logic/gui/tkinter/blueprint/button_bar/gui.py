import tkinter as tk
from typing import List, Dict, Any, Callable, Optional
from logic.gui.tkinter.blueprint.base import BaseGUIWindow

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
                 focus_interval: int = 45,
                 disable_auto_unlock: bool = False):
        """
        Args:
            title: Window title.
            timeout: Auto-close timeout in seconds.
            internal_dir: Directory for localization files.
            buttons: List of dicts with keys text, cmd, bg, fg, font, close_on_click, disable_seconds.
            instruction: Optional text to display above buttons.
            window_size: Tkinter geometry string.
            on_startup: Callback executed after UI setup but before mainloop.
            focus_interval: Seconds between periodic focus/bell prompts.
            disable_auto_unlock: If True, skip keyboard/focus auto-unlock (for CDP mode).
        """
        super().__init__(title, timeout, internal_dir, focus_interval=focus_interval)
        self.buttons_config = buttons
        self.instruction_text = instruction
        self.window_size = window_size
        self.on_startup_callback = on_startup
        self._disable_auto_unlock = disable_auto_unlock

    def setup_ui(self):
        from logic.gui.tkinter.style import get_button_style, get_label_style
        self.root.geometry(self.window_size)
        self.root.resizable(True, True)
        
        main_frame = tk.Frame(self.root, padx=15, pady=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Optional Instruction Area (using Text for markdown-like bolding)
        self._text_widget = None
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
            self._text_widget = text_widget

        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, expand=True)
        
        delayed_buttons = []
        self._keyboard_available = self._check_keyboard_capture()
        try:
            from logic.utils.accessibility.keyboard.monitor import _log
            _log(f"ButtonBar.setup_ui: keyboard_available={self._keyboard_available}")
        except Exception:
            pass
        
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
            
            return_value = btn_cfg.get("return_value", text)

            def create_cmd(actual_cmd, should_close, btn_ref_list, callback, ret_val=return_value):
                def wrapper():
                    if callback and btn_ref_list:
                        callback(btn_ref_list[0])
                    if actual_cmd:
                        actual_cmd()
                    if should_close:
                        self.finalize("success", ret_val)
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
        self._delayed_buttons = delayed_buttons
        self._buttons_unlocked = False

        _cmd_hint = " - Cmd" if not self._disable_auto_unlock else ""
        for btn, original_text, seconds in delayed_buttons:
            btn.config(state="disabled", text=f"{original_text} ({seconds}s{_cmd_hint})")
            def countdown(b=btn, t=original_text, remaining=seconds, hint=_cmd_hint):
                if self._buttons_unlocked:
                    return
                if remaining <= 1:
                    b.config(state="normal", text=t)
                    return
                b.config(text=f"{t} ({remaining - 1}s{hint})")
                self.root.after(1000, lambda: countdown(b, t, remaining - 1, hint))
            self.root.after(1000, lambda b=btn, t=original_text, s=seconds, h=_cmd_hint: countdown(b, t, s, h))

        if delayed_buttons:
            self._global_listener = None
            self._focus_lost = False
            if not self._disable_auto_unlock:
                self._start_focus_detection()
                self._start_global_key_listener()
                self._start_tkinter_key_detection()

        if self.on_startup_callback:
            self.root.after(100, self.on_startup_callback)

    @staticmethod
    def _check_keyboard_capture() -> bool:
        """Check if global keyboard capture (pynput + accessibility) actually works.
        
        On macOS, even if AXIsProcessTrusted() returns True and the listener
        thread is alive, the subprocess may not actually receive events from
        other applications. A thread-alive check is insufficient.
        
        We verify by checking the Quartz CGEvent tap status directly when
        available, falling back to False on macOS subprocesses where the
        event tap is known to be unreliable.
        """
        try:
            from logic.utils.accessibility.keyboard.monitor import is_available, check_accessibility_trusted, _log, _init_log
            _init_log()
            avail = is_available()
            trusted = check_accessibility_trusted()
            if not (avail and trusted):
                _log(f"ButtonBar._check_keyboard_capture: pynput={avail}, accessibility={trusted} -> False")
                return False

            import platform
            if platform.system() == "Darwin":
                # On macOS, subprocess pynput listeners often fail to receive
                # global events despite thread being alive. Only trust it if
                # running in the main process that was granted accessibility.
                import os
                # If we're a subprocess (PPID != 1 and not the login shell),
                # the event tap is very likely not working.
                ppid = os.getppid()
                _log(f"ButtonBar._check_keyboard_capture: macOS ppid={ppid}, pid={os.getpid()}")
                # Returning False forces the short 2s countdown + focus detection
                _log("ButtonBar._check_keyboard_capture: macOS subprocess -> False (unreliable)")
                return False

            import time
            from pynput import keyboard
            test_listener = keyboard.Listener(on_press=lambda k: None)
            test_listener.daemon = True
            test_listener.start()
            time.sleep(0.3)
            alive = test_listener.is_alive()
            test_listener.stop()
            _log(f"ButtonBar._check_keyboard_capture: listener_alive={alive}")
            return alive
        except Exception as e:
            try:
                from logic.utils.accessibility.keyboard.monitor import _log
                _log(f"ButtonBar._check_keyboard_capture: exception {e}")
            except Exception:
                pass
            return False

    def _start_focus_detection(self):
        """Detect when window loses then regains focus to unlock buttons.
        
        When the user switches away (to paste in browser) and comes back,
        the buttons unlock. No special permissions required.
        """
        def _flog(msg):
            try:
                from logic.utils.accessibility.keyboard.monitor import _log
                _log(msg)
            except Exception:
                pass

        _flog("ButtonBar: focus detection started")

        def on_focus_out(event):
            if event.widget == self.root:
                self._focus_lost = True
                _flog("ButtonBar: FocusOut (user switched away)")

        def on_focus_in(event):
            if event.widget == self.root:
                _flog(f"ButtonBar: FocusIn (focus_lost={self._focus_lost}, unlocked={self._buttons_unlocked})")
                if self._focus_lost and not self._buttons_unlocked:
                    self._unlock_delayed_buttons(reason="focus_regained")

        self.root.bind("<FocusOut>", on_focus_out)
        self.root.bind("<FocusIn>", on_focus_in)

    def _start_global_key_listener(self):
        """Start a pynput global keyboard listener to detect paste+Enter.
        
        Skipped entirely when keyboard capture is unavailable (no pynput
        or no Accessibility permissions), falling back to focus detection
        and timer only.
        """
        from logic.utils.accessibility.keyboard.monitor import _log
        if not self._keyboard_available:
            _log("ButtonBar: skipping global key listener (keyboard capture unavailable)")
            return
        from logic.utils.accessibility.keyboard.monitor import start_paste_enter_listener
        _log("ButtonBar: starting paste+enter global listener")
        self._global_listener = start_paste_enter_listener(
            lambda: self.root.after(0, lambda: self._unlock_delayed_buttons(reason="paste_enter_detected"))
        )

    def _start_tkinter_key_detection(self):
        """Detect Command key press to unlock buttons (works when window has focus).

        On macOS, pynput global capture fails in subprocesses and FocusIn
        is unreliable. Detecting Command key in tkinter is the most
        reliable local mechanism.
        """
        def _klog(msg):
            try:
                from logic.utils.accessibility.keyboard.monitor import _log
                _log(msg)
            except Exception:
                pass

        def on_tk_key(event):
            if event.keysym in ('Meta_L', 'Meta_R', 'Control_L', 'Control_R',
                                'Super_L', 'Super_R'):
                _klog(f"ButtonBar: TK_KEY {event.keysym} -> unlocking")
                if not self._buttons_unlocked:
                    self._unlock_delayed_buttons(reason="command_key")

        self.root.bind("<Key>", on_tk_key)

    def _stop_global_key_listener(self):
        from logic.utils.accessibility.keyboard.monitor import stop_listener
        if hasattr(self, '_global_listener'):
            stop_listener(self._global_listener)
            self._global_listener = None

    def _unlock_delayed_buttons(self, reason="unknown"):
        """Immediately unlock all countdown-disabled buttons."""
        if self._buttons_unlocked:
            return
        self._buttons_unlocked = True
        try:
            from logic.utils.accessibility.keyboard.monitor import _log
            _log(f"ButtonBar: unlocking buttons (reason={reason})")
        except Exception:
            pass
        for btn, original_text, _ in self._delayed_buttons:
            try:
                btn.config(state="normal", text=original_text)
            except Exception:
                pass
        self._stop_global_key_listener()

    def update_status_line(self, new_status: str):
        """Update the last line of the instruction text (used for CDP status updates)."""
        if not self._text_widget:
            return
        try:
            tw = self._text_widget
            tw.config(state="normal")
            content = tw.get("1.0", "end-1c")
            last_nl = content.rfind("\n")
            if last_nl >= 0:
                tw.delete(f"1.0+{last_nl + 1}c", "end")
                tw.insert("end", new_status)
            else:
                tw.delete("1.0", "end")
                tw.insert("end", new_status)
            tw.config(state="disabled")
        except Exception:
            pass

    def run(self, custom_id: Optional[str] = None):
        super().run(self.setup_ui, custom_id=custom_id)
        self._stop_global_key_listener()

