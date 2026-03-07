"""
Chatbot Blueprint - A multi-session chat GUI with sidebar and message display.

Inheritance:
    BaseGUIWindow (base.py) -> ChatbotWindow (this file)

Features:
    - Left sidebar with session list (create, switch, delete).
    - Main chat area with scrollable message bubbles.
    - Bottom input area with text entry and send button.
    - Status bar for pipeline progress.
    - Dark theme by default, customizable via color dict.
    - Session auto-titling from first assistant response.

External control interface (for testing and automation):
    - ChatbotWindow.cmd_create_session()         Create and switch to a new session.
    - ChatbotWindow.cmd_send_message(text)        Send a message in the current session.
    - ChatbotWindow.cmd_get_status()              Return current pipeline status.
    - ChatbotWindow.cmd_list_sessions()           Return list of session IDs and titles.
    - ChatbotWindow.cmd_switch_session(id)        Switch to a specific session.
    - ChatbotWindow.cmd_get_messages()            Return messages for current session.
    - ChatbotWindow.cmd_stop_pipeline()           Stop the running pipeline.

Dependency chain:
    BaseGUIWindow (base.py) -> ChatbotWindow (this file)
"""
import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List

_script_path = Path(__file__).resolve()
_project_root = _script_path.parent.parent.parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.gui.tkinter.blueprint.base import BaseGUIWindow

# Default dark color scheme
DEFAULT_COLORS = {
    "bg": "#1e1e2e",
    "sidebar_bg": "#181825",
    "sidebar_hover": "#313244",
    "sidebar_selected": "#45475a",
    "chat_bg": "#1e1e2e",
    "input_bg": "#313244",
    "input_fg": "#cdd6f4",
    "text_fg": "#cdd6f4",
    "text_dim": "#6c7086",
    "user_msg_bg": "#45475a",
    "assistant_msg_bg": "#313244",
    "system_msg_fg": "#f9e2af",
    "accent": "#89b4fa",
    "accent_hover": "#74c7ec",
    "border": "#45475a",
    "error": "#f38ba8",
    "success": "#a6e3a1",
}

DEFAULT_FONTS = {
    "title": ("SF Pro Display", 14, "bold"),
    "sidebar": ("SF Pro Text", 12),
    "message": ("SF Mono", 12),
    "input": ("SF Mono", 13),
    "status": ("SF Pro Text", 11),
    "button": ("SF Pro Text", 12, "bold"),
    "role": ("SF Pro Text", 10, "bold"),
}


class ChatbotWindow(BaseGUIWindow):
    """A reusable chatbot GUI blueprint with sidebar session management.

    Constructor args:
        title:           Window title.
        timeout:         Auto-close timeout (0 = no timeout).
        internal_dir:    Directory for localization.
        tool_name:       Tool identifier for instance registry.
        on_send:         Callback(session_id, text) when user sends a message.
        session_provider: Object with list_sessions(), create_session(),
                         get_session(id), add_message(id, role, content),
                         update_title(id, title), complete_session(id), 
                         delete_session(id) methods.
        colors:          Optional color overrides (dict).
        fonts:           Optional font overrides (dict).
        window_size:     Tkinter geometry string.
        focus_interval:  Seconds between periodic focus (0 = disabled).
    """

    def __init__(self, title: str, timeout: int, internal_dir: str,
                 tool_name: str = None,
                 on_send: Optional[Callable] = None,
                 session_provider=None,
                 colors: Optional[Dict[str, str]] = None,
                 fonts: Optional[Dict] = None,
                 window_size: str = "1100x700",
                 focus_interval: int = 0):
        super().__init__(title, timeout, internal_dir,
                         tool_name=tool_name, focus_interval=focus_interval)
        self.on_send = on_send
        self.session_provider = session_provider
        self.colors = {**DEFAULT_COLORS, **(colors or {})}
        self.fonts = {**DEFAULT_FONTS, **(fonts or {})}
        self.window_size = window_size
        self.current_session_id: Optional[str] = None
        self._session_frames: Dict[str, Dict] = {}
        self._status_text = "Ready."
        self._pipeline_running = False

    def setup_ui(self):
        """Build the UI layout."""
        import tkinter as tk
        C = self.colors
        F = self.fonts

        self.root.geometry(self.window_size)
        self.root.minsize(800, 500)
        self.root.configure(bg=C["bg"])

        main_frame = tk.Frame(self.root, bg=C["bg"])
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ---- Sidebar ----
        self.sidebar = tk.Frame(main_frame, bg=C["sidebar_bg"], width=240)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        sidebar_header = tk.Frame(self.sidebar, bg=C["sidebar_bg"])
        sidebar_header.pack(fill=tk.X, padx=10, pady=(15, 5))

        tk.Label(sidebar_header, text=self.title, font=F["title"],
                 fg=C["accent"], bg=C["sidebar_bg"]).pack(side=tk.LEFT)

        new_btn = tk.Label(sidebar_header, text="+",
                           font=("SF Pro Display", 18, "bold"),
                           fg=C["accent"], bg=C["sidebar_bg"], cursor="hand2")
        new_btn.pack(side=tk.RIGHT, padx=(0, 5))
        new_btn.bind("<Button-1>", lambda e: self.cmd_create_session())
        new_btn.bind("<Enter>", lambda e: new_btn.config(fg=C["accent_hover"]))
        new_btn.bind("<Leave>", lambda e: new_btn.config(fg=C["accent"]))

        tk.Frame(self.sidebar, bg=C["border"], height=1).pack(fill=tk.X, padx=10, pady=5)

        self.session_list_frame = tk.Frame(self.sidebar, bg=C["sidebar_bg"])
        self.session_list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ---- Separator ----
        tk.Frame(main_frame, bg=C["border"], width=1).pack(side=tk.LEFT, fill=tk.Y)

        # ---- Chat Area ----
        chat_frame = tk.Frame(main_frame, bg=C["chat_bg"])
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Messages
        msg_container = tk.Frame(chat_frame, bg=C["chat_bg"])
        msg_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 0))

        self.msg_canvas = tk.Canvas(msg_container, bg=C["chat_bg"],
                                     highlightthickness=0, bd=0)
        self.msg_scrollbar = tk.Scrollbar(msg_container, orient=tk.VERTICAL,
                                           command=self.msg_canvas.yview)
        self.msg_inner = tk.Frame(self.msg_canvas, bg=C["chat_bg"])

        self.msg_inner.bind("<Configure>",
            lambda e: self.msg_canvas.configure(scrollregion=self.msg_canvas.bbox("all")))

        self.msg_canvas_window = self.msg_canvas.create_window(
            (0, 0), window=self.msg_inner, anchor="nw")
        self.msg_canvas.configure(yscrollcommand=self.msg_scrollbar.set)

        self.msg_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.msg_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.msg_canvas.bind("<Configure>", self._on_canvas_configure)
        self.msg_canvas.bind_all("<MouseWheel>",
            lambda e: self.msg_canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        # Status bar
        self.status_label = tk.Label(
            chat_frame, text=self._status_text, font=F["status"],
            fg=C["text_dim"], bg=C["chat_bg"], anchor="w")
        self.status_label.pack(fill=tk.X, padx=20, pady=(5, 0))

        # Input area
        input_frame = tk.Frame(chat_frame, bg=C["input_bg"],
                                highlightbackground=C["border"],
                                highlightthickness=1, bd=0)
        input_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

        self.input_text = tk.Text(
            input_frame, font=F["input"], height=3,
            bg=C["input_bg"], fg=C["input_fg"],
            insertbackground=C["text_fg"],
            bd=0, highlightthickness=0, wrap=tk.WORD,
            padx=10, pady=8)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        send_btn = tk.Label(
            input_frame, text="Send", font=F["button"],
            fg=C["accent"], bg=C["input_bg"],
            cursor="hand2", padx=15, pady=8)
        send_btn.pack(side=tk.RIGHT)
        send_btn.bind("<Button-1>", lambda e: self._handle_send())
        send_btn.bind("<Enter>", lambda e: send_btn.config(fg=C["accent_hover"]))
        send_btn.bind("<Leave>", lambda e: send_btn.config(fg=C["accent"]))

        self.input_text.bind("<Return>", self._on_enter)

        # Load existing sessions
        self._load_sessions()

    def _on_canvas_configure(self, event):
        self.msg_canvas.itemconfig(self.msg_canvas_window, width=event.width)

    def _on_enter(self, event):
        if event.state & 0x1:
            return
        self._handle_send()
        return "break"

    def get_current_state(self) -> Any:
        """Return current state for Interface I."""
        return {
            "session_id": self.current_session_id,
            "pipeline_running": self._pipeline_running,
            "sessions": [
                {"id": s.id, "title": s.get_display_title(), "status": s.status}
                for s in (self.session_provider.list_sessions() if self.session_provider else [])
            ]
        }

    # ---- Session Management ----

    def _load_sessions(self):
        if not self.session_provider:
            return
        for session in self.session_provider.list_sessions():
            self._add_session_to_sidebar(session)

    def _add_session_to_sidebar(self, session):
        import tkinter as tk
        C = self.colors

        frame = tk.Frame(self.session_list_frame, bg=C["sidebar_bg"], cursor="hand2")
        frame.pack(fill=tk.X, pady=1)

        title = session.get_display_title()
        if len(title) > 28:
            title = title[:28] + "..."

        label = tk.Label(frame, text=title, font=self.fonts["sidebar"],
                         fg=C["text_fg"], bg=C["sidebar_bg"],
                         anchor="w", padx=12, pady=8)
        label.pack(fill=tk.X)

        sid = session.id
        for widget in (frame, label):
            widget.bind("<Button-1>", lambda e, s=sid: self.cmd_switch_session(s))
            widget.bind("<Enter>", lambda e, f=frame, l=label: (
                f.config(bg=C["sidebar_hover"]), l.config(bg=C["sidebar_hover"])))
            widget.bind("<Leave>", lambda e, f=frame, l=label, s=sid: (
                f.config(bg=C["sidebar_selected"] if s == self.current_session_id else C["sidebar_bg"]),
                l.config(bg=C["sidebar_selected"] if s == self.current_session_id else C["sidebar_bg"])))

        self._session_frames[sid] = {"frame": frame, "label": label}

    def _update_sidebar_selection(self):
        C = self.colors
        for sid, widgets in self._session_frames.items():
            bg = C["sidebar_selected"] if sid == self.current_session_id else C["sidebar_bg"]
            widgets["frame"].config(bg=bg)
            widgets["label"].config(bg=bg)

    def _render_messages(self):
        import tkinter as tk

        for widget in self.msg_inner.winfo_children():
            widget.destroy()

        if not self.current_session_id or not self.session_provider:
            welcome = tk.Label(self.msg_inner,
                text="Create a new session to start.\nClick '+' in the sidebar.",
                font=self.fonts["message"], fg=self.colors["text_dim"],
                bg=self.colors["chat_bg"], justify=tk.CENTER)
            welcome.pack(expand=True, pady=100)
            return

        session = self.session_provider.get_session(self.current_session_id)
        if not session:
            return

        for msg in session.messages:
            self._render_single_message(msg["role"], msg["content"])

        self.msg_canvas.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)

    def _render_single_message(self, role: str, content: str):
        import tkinter as tk
        C = self.colors

        config = {
            "user": (C["user_msg_bg"], C["text_fg"], tk.E, 60, 10, "You"),
            "assistant": (C["assistant_msg_bg"], C["text_fg"], tk.W, 10, 60, "Agent"),
            "system": (C["chat_bg"], C["system_msg_fg"], tk.W, 10, 10, "System"),
            "feedback": (C["chat_bg"], C["text_dim"], tk.W, 20, 20, "Output"),
        }.get(role, (C["chat_bg"], C["text_fg"], tk.W, 10, 10, role))

        bg, fg, anchor, padx_l, padx_r, role_name = config

        wrapper = tk.Frame(self.msg_inner, bg=C["chat_bg"])
        wrapper.pack(fill=tk.X, padx=(padx_l, padx_r), pady=4)

        tk.Label(wrapper, text=role_name, font=self.fonts["role"],
                 fg=C["text_dim"], bg=C["chat_bg"], anchor="w").pack(fill=tk.X, padx=5)

        bubble = tk.Frame(wrapper, bg=bg, bd=0,
                           highlightbackground=C["border"], highlightthickness=1)
        bubble.pack(fill=tk.X, pady=(2, 0))

        text_widget = tk.Text(bubble, font=self.fonts["message"], bg=bg, fg=fg,
                               wrap=tk.WORD, bd=0, highlightthickness=0,
                               padx=12, pady=8, height=1)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)

        def update_height(event=None):
            try:
                lines = int(text_widget.index("end-1c").split(".")[0])
                text_widget.config(height=min(lines, 30))
            except Exception:
                pass

        text_widget.pack(fill=tk.X)
        self.root.after(50, update_height)

    def _handle_send(self):
        import tkinter as tk
        text = self.input_text.get("1.0", tk.END).strip()
        if not text:
            return
        self.input_text.delete("1.0", tk.END)

        if not self.current_session_id:
            self.cmd_create_session()

        if self._pipeline_running:
            self.set_status("Agent is still processing...")
            return

        self._render_single_message("user", text)
        self.msg_canvas.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)

        if self.on_send:
            self.on_send(self.current_session_id, text)

    # ---- Public API (thread-safe updates from pipeline) ----

    def append_message(self, role: str, content: str):
        """Thread-safe: add a message to the current view."""
        def _do():
            if not self.current_session_id:
                return
            self._render_single_message(role, content)
            self.msg_canvas.update_idletasks()
            self.msg_canvas.yview_moveto(1.0)
        self.callback_queue.put(_do)

    def set_status(self, text: str):
        """Thread-safe: update status bar."""
        self._status_text = text
        def _do():
            try:
                self.status_label.config(text=text)
            except Exception:
                pass
        self.callback_queue.put(_do)

    def set_pipeline_running(self, running: bool):
        """Thread-safe: update pipeline state."""
        self._pipeline_running = running

    def update_session_title(self, session_id: str, title: str):
        """Thread-safe: update sidebar title."""
        def _do():
            if session_id in self._session_frames:
                display = title[:28] + "..." if len(title) > 28 else title
                self._session_frames[session_id]["label"].config(text=display)
        self.callback_queue.put(_do)

    # ---- External Control Commands (cmd_*) ----

    def cmd_create_session(self) -> Optional[str]:
        """Create and switch to a new session. Returns session ID."""
        if not self.session_provider:
            return None
        session = self.session_provider.create_session()
        self._add_session_to_sidebar(session)
        self.cmd_switch_session(session.id)
        return session.id

    def cmd_switch_session(self, session_id: str):
        """Switch to viewing a specific session."""
        self.current_session_id = session_id
        self._update_sidebar_selection()
        self._render_messages()

    def cmd_send_message(self, text: str):
        """Programmatically send a message in the current session."""
        if not self.current_session_id:
            self.cmd_create_session()
        self._render_single_message("user", text)
        self.msg_canvas.update_idletasks()
        self.msg_canvas.yview_moveto(1.0)
        if self.on_send:
            self.on_send(self.current_session_id, text)

    def cmd_get_status(self) -> Dict[str, Any]:
        """Return current status."""
        return {
            "session_id": self.current_session_id,
            "pipeline_running": self._pipeline_running,
            "status_text": self._status_text,
        }

    def cmd_list_sessions(self) -> List[Dict[str, str]]:
        """Return list of sessions."""
        if not self.session_provider:
            return []
        return [
            {"id": s.id, "title": s.get_display_title(), "status": s.status}
            for s in self.session_provider.list_sessions()
        ]

    def cmd_get_messages(self) -> List[Dict[str, str]]:
        """Return messages for the current session."""
        if not self.current_session_id or not self.session_provider:
            return []
        session = self.session_provider.get_session(self.current_session_id)
        if not session:
            return []
        return session.messages

    def cmd_stop_pipeline(self):
        """Signal to stop the running pipeline."""
        self._pipeline_running = False
        self.set_status("Pipeline stop requested.")

    def launch(self, custom_id: Optional[str] = None):
        """Convenience launcher using BaseGUIWindow.run()."""
        self.run(self.setup_ui, custom_id=custom_id)
