"""OPENCLAW HTML Chat GUI — uses the shared HTML chatbot blueprint.

Wires the HTML chatbot server to OPENCLAW's pipeline and session manager.
Supports two backends:
  - ``yuanbao_web``: Tencent Yuanbao via CDMCP (original)
  - ``nvidia_glm47``: GLM-4.7 via NVIDIA Build API (compliant)
"""
from typing import Optional

from logic.gui.html.blueprint.chatbot.server import ChatbotServer
from tool.OPENCLAW.logic.session import SessionManager


class OpenClawChatHTML:
    """OPENCLAW-specific wrapper around the HTML ChatbotServer."""

    def __init__(self, session_mgr: SessionManager, cdp_port: int = 9222,
                 backend: str = "nvidia_glm47"):
        self.session_mgr = session_mgr
        self.cdp_port = cdp_port
        self.backend = backend
        self.current_pipeline = None
        self.server: Optional[ChatbotServer] = None

    def _create_pipeline(self, session, on_message, on_status, on_title):
        """Create the appropriate pipeline based on backend selection."""
        if self.backend == "nvidia_glm47":
            from tool.OPENCLAW.logic.pipeline_api import APIPipeline
            from tool.LLM.logic.providers.nvidia_glm47 import NvidiaGLM47Provider
            provider = NvidiaGLM47Provider()
            return APIPipeline(
                session_mgr=self.session_mgr,
                session=session,
                provider=provider,
                on_message=on_message,
                on_status=on_status,
                on_title=on_title,
            )
        else:
            from tool.OPENCLAW.logic.pipeline import Pipeline
            return Pipeline(
                session_mgr=self.session_mgr,
                session=session,
                on_message=on_message,
                on_status=on_status,
                on_title=on_title,
                cdp_port=self.cdp_port,
            )

    def _on_send(self, session_id: str, text: str):
        """Called when user sends a message. Starts the pipeline."""
        session = self.session_mgr.get_session(session_id)
        if not session:
            return

        self.session_mgr.add_message(session_id, "user", text)

        if self.current_pipeline and self.current_pipeline.is_running():
            if self.server:
                self.server.set_status("Agent is still processing...")
            return

        def on_message(role, content):
            if self.server:
                self.server.send_message_to_gui(session_id, role, content)

        def on_status(status_text):
            if self.server:
                self.server.set_status(status_text)

        def on_title(title):
            if self.server:
                self.server.update_session_title(session_id, title)

        self.current_pipeline = self._create_pipeline(
            session, on_message, on_status, on_title)

        if self.server:
            self.server.set_pipeline_running(True)
            self.server.set_typing(True)

        def on_done():
            if self.server:
                self.server.set_pipeline_running(False)
                self.server.set_typing(False)

        self.current_pipeline.start(text)

    def run(self):
        """Launch the OPENCLAW HTML chatbot server and open in browser."""
        self.server = ChatbotServer(
            title="OPENCLAW",
            on_send=self._on_send,
            session_provider=self.session_mgr,
        )
        self.server.start()
        self.server.open_browser()
        print(f"  OPENCLAW GUI running at http://localhost:{self.server.port}/", flush=True)
        print(f"  WebSocket at ws://localhost:{self.server.ws_port}/ws", flush=True)
        self.server.wait()
