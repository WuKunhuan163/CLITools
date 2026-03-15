"""Live agent server for the LLM Agent GUI.

Wires ConversationManager → SSE → browser, with HTTP API endpoints
for message sending, session management, and automation control.

Usage:
    from tool.LLM.logic.gui.agent_server import start_agent_server
    server = start_agent_server(port=0)
    # → http://localhost:{port}/

API Endpoints:
    POST /api/send     {"session_id": "...", "text": "..."}
    POST /api/session  {"title": "..."}
    POST /api/rename   {"session_id": "...", "title": "..."}
    POST /api/delete   {"session_id": "..."}
    GET  /api/sessions
    GET  /api/state
    POST /api/input    {"session_id": "...", "text": "..."}
                       Simulates typing into the input box then clicking send.
                       The browser receives an 'inject_input' SSE event to
                       animate the text appearing, then auto-submits.
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional

_dir = Path(__file__).resolve().parent
_root = _dir.parent.parent.parent.parent
sys.path.insert(0, str(_root))

from tool.LLM.logic.gui.conversation import ConversationManager


class AgentServer:
    """Manages the live agent server lifecycle."""

    def __init__(
        self,
        provider_name: str = "zhipu-glm-4-flash",
        system_prompt: str = "",
        enable_tools: bool = False,
        port: int = 0,
    ):
        self.provider_name = provider_name
        self.system_prompt = system_prompt
        self.enable_tools = enable_tools
        self.port = port

        self._mgr = ConversationManager(
            provider_name=provider_name,
            system_prompt=system_prompt,
            enable_tools=enable_tools,
        )
        self._server = None
        self._default_session_id = None

    def _api_handler(self, method: str, path: str, body: Optional[dict]) -> dict:
        """Route API requests to ConversationManager methods."""
        path = path.split("?")[0]

        if method == "GET":
            if path == "/api/sessions":
                return {"ok": True, "sessions": self._mgr.list_sessions()}
            elif path == "/api/state":
                return {"ok": True, "state": self._mgr.get_state()}
            return {"ok": False, "error": "Unknown endpoint"}

        if method == "POST":
            body = body or {}

            if path == "/api/send":
                sid = body.get("session_id") or self._default_session_id
                text = body.get("text", "").strip()
                if not sid:
                    return {"ok": False, "error": "No active session"}
                if not text:
                    return {"ok": False, "error": "Empty message"}
                session = self._mgr.get_session(sid)
                if not session:
                    return {"ok": False, "error": f"Session {sid} not found"}
                self._mgr.send_message(sid, text, blocking=False)
                return {"ok": True, "session_id": sid}

            elif path == "/api/input":
                sid = body.get("session_id") or self._default_session_id
                text = body.get("text", "").strip()
                if not sid or not text:
                    return {"ok": False, "error": "Missing session_id or text"}
                self._push_sse({
                    "type": "inject_input",
                    "session_id": sid,
                    "text": text,
                })
                return {"ok": True, "session_id": sid}

            elif path == "/api/session":
                title = body.get("title", "New Task")
                sid = self._mgr.new_session(title=title)
                self._default_session_id = sid
                self._push_sse({
                    "type": "session_created",
                    "id": sid,
                    "title": title,
                })
                return {"ok": True, "session_id": sid}

            elif path == "/api/rename":
                sid = body.get("session_id", "")
                title = body.get("title", "")
                if sid and title:
                    self._mgr.rename_session(sid, title)
                    return {"ok": True}
                return {"ok": False, "error": "Missing session_id or title"}

            elif path == "/api/delete":
                sid = body.get("session_id", "")
                if sid:
                    self._mgr.delete_session(sid)
                    remaining = self._mgr.list_sessions()
                    self._default_session_id = remaining[-1]["id"] if remaining else None
                    return {"ok": True}
                return {"ok": False, "error": "Missing session_id"}

            return {"ok": False, "error": "Unknown endpoint"}

        return {"ok": False, "error": "Method not allowed"}

    def _push_sse(self, evt: dict):
        if self._server:
            self._server.push_event(evt)

    def _on_mgr_event(self, evt: dict):
        """Forward ConversationManager events to SSE."""
        self._push_sse(evt)

    def start(self, open_browser: bool = True):
        """Start the live agent server."""
        from logic.serve.html_server import LocalHTMLServer

        html_path = str(_dir / "agent_live.html")

        self._server = LocalHTMLServer(
            html_path=html_path,
            port=self.port,
            title="LLM Agent Live",
            api_handler=self._api_handler,
            enable_sse=True,
        )

        self._mgr.on_event(self._on_mgr_event)

        sid = self._mgr.new_session(title="New Task")
        self._default_session_id = sid

        self._server.start()

        if open_browser:
            self._server.open_browser()

        return self._server

    def stop(self):
        if self._server:
            self._server.stop()

    @property
    def url(self) -> str:
        return self._server.url if self._server else ""

    @property
    def default_session_id(self) -> Optional[str]:
        return self._default_session_id


def start_agent_server(
    provider_name: str = "zhipu-glm-4-flash",
    system_prompt: str = "",
    enable_tools: bool = False,
    port: int = 0,
    open_browser: bool = True,
) -> AgentServer:
    """Convenience function to start the live agent server.

    Returns the AgentServer instance (server is already running).
    """
    agent = AgentServer(
        provider_name=provider_name,
        system_prompt=system_prompt,
        enable_tools=enable_tools,
        port=port,
    )
    agent.start(open_browser=open_browser)
    return agent
