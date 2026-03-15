"""OPENCLAW Chat GUI — uses the shared chatbot blueprint.

This module wires the chatbot blueprint to OPENCLAW's pipeline and session manager.
The blueprint (logic/gui/tkinter/blueprint/chatbot/) handles all UI rendering;
this module only provides the glue logic.
"""
from pathlib import Path
from typing import Optional

from interface.gui import ChatbotWindow
from tool.OPENCLAW.logic.session import SessionManager
from tool.OPENCLAW.logic.pipeline import Pipeline

OPENCLAW_COLORS = {
    "bg": "#0d1117",
    "sidebar_bg": "#161b22",
    "sidebar_hover": "#1c2128",
    "sidebar_selected": "#21262d",
    "chat_bg": "#0d1117",
    "input_bg": "#1c2128",
    "input_fg": "#e6edf3",
    "text_fg": "#e6edf3",
    "text_dim": "#484f58",
    "user_msg_bg": "#21262d",
    "assistant_msg_bg": "#161b22",
    "system_msg_fg": "#d29922",
    "accent": "#e63946",
    "accent_hover": "#c41e3a",
    "border": "#30363d",
    "error": "#f85149",
    "success": "#3fb950",
}


class OpenClawChat:
    """OPENCLAW-specific wrapper around ChatbotWindow."""

    def __init__(self, session_mgr: SessionManager, cdp_port: int = 9222):
        self.session_mgr = session_mgr
        self.cdp_port = cdp_port
        self.current_pipeline: Optional[Pipeline] = None
        self.gui: Optional[ChatbotWindow] = None

    def _on_send(self, session_id: str, text: str):
        """Called when user sends a message. Starts the pipeline."""
        session = self.session_mgr.get_session(session_id)
        if not session:
            return

        self.session_mgr.add_message(session_id, "user", text)

        if self.current_pipeline and self.current_pipeline.is_running():
            if self.gui:
                self.gui.set_status("Agent is still processing...")
            return

        def on_message(role, content):
            if self.gui:
                self.gui.append_message(role, content)

        def on_status(status_text):
            if self.gui:
                self.gui.set_status(status_text)

        def on_title(title):
            if self.gui:
                self.gui.update_session_title(session_id, title)

        self.current_pipeline = Pipeline(
            session_mgr=self.session_mgr,
            session=session,
            on_message=on_message,
            on_status=on_status,
            on_title=on_title,
            cdp_port=self.cdp_port,
        )
        if self.gui:
            self.gui.set_pipeline_running(True)

        def on_done():
            if self.gui:
                self.gui.set_pipeline_running(False)

        self.current_pipeline.start(text)

    def run(self):
        """Launch the OPENCLAW chatbot GUI."""
        internal_dir = str(Path(__file__).resolve().parent.parent)

        self.gui = ChatbotWindow(
            title="OPENCLAW",
            timeout=0,
            internal_dir=internal_dir,
            tool_name="OPENCLAW",
            on_send=self._on_send,
            session_provider=self.session_mgr,
            colors=OPENCLAW_COLORS,
            focus_interval=0,
        )
        self.gui.launch(custom_id="openclaw-chat")
