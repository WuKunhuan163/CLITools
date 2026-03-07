"""HTML Chatbot Blueprint — Lightweight WebSocket Server

Serves the chatbot HTML page and provides a WebSocket + REST API
for bidirectional communication between the GUI and a tool's backend logic.

Usage:
    from logic.gui.html.blueprint.chatbot.server import ChatbotServer

    server = ChatbotServer(
        title="OPENCLAW",
        port=8765,
        on_send=my_send_handler,       # called with (session_id, text)
        session_provider=my_sessions,   # implements list/create/get/delete
    )
    server.start()        # non-blocking, launches in background thread
    server.open_browser()  # opens in Chrome via CDMCP or default browser
    server.wait()          # blocks until server shuts down
"""
import asyncio
import json
import threading
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from functools import partial
import socket
import logging

log = logging.getLogger("chatbot-html")

BLUEPRINT_DIR = Path(__file__).resolve().parent


class _StaticHandler(SimpleHTTPRequestHandler):
    """Serve the blueprint's static files + REST API."""

    server_instance = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BLUEPRINT_DIR), **kwargs)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self._serve_index()
        elif self.path.startswith("/api/"):
            self._handle_api_get()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._handle_api_post()
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"):
            self._handle_api_delete()
        else:
            self.send_error(404)

    def _serve_index(self):
        srv = self.server_instance
        if not srv:
            super().do_GET()
            return

        html = (BLUEPRINT_DIR / "index.html").read_text(encoding="utf-8")
        config_js = json.dumps({
            "title": srv.title,
            "wsUrl": f"ws://localhost:{srv.ws_port}/ws",
            "apiUrl": f"http://localhost:{srv.port}/api",
        })
        inject = f'<script>window.__OPENCLAW_CONFIG = {config_js};</script>'
        html = html.replace("</head>", f"{inject}\n</head>")

        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    def _handle_api_get(self):
        srv = self.server_instance
        if not srv or not srv.session_provider:
            self._json_response({"ok": False, "error": "No session provider"})
            return

        path = self.path.split("?")[0]

        if path == "/api/status":
            sessions = srv.session_provider.list_sessions()
            self._json_response({
                "ok": True,
                "pipeline_running": srv._pipeline_running,
                "sessions": [_serialize_session(s) for s in sessions],
            })

        elif path.startswith("/api/sessions/") and path.endswith("/messages"):
            sid = path.split("/")[3]
            s = srv.session_provider.get_session(sid)
            if s:
                msgs = [{"role": m.get("role", "system"), "content": m.get("content", "")}
                        for m in getattr(s, "messages", [])]
                self._json_response({"ok": True, "messages": msgs})
            else:
                self._json_response({"ok": False, "error": "Session not found"}, 404)
        else:
            self._json_response({"ok": False, "error": "Unknown endpoint"}, 404)

    def _handle_api_post(self):
        srv = self.server_instance
        if not srv:
            self._json_response({"ok": False, "error": "Server not ready"})
            return

        path = self.path.split("?")[0]

        if path == "/api/sessions":
            s = srv.session_provider.create_session()
            self._json_response({"ok": True, "session": _serialize_session(s)})

        elif path == "/api/send":
            data = self._read_body()
            sid = data.get("session_id")
            text = data.get("text", "")
            if sid and text and srv.on_send:
                srv.on_send(sid, text)
            self._json_response({"ok": True})
        else:
            self._json_response({"ok": False, "error": "Unknown endpoint"}, 404)

    def _handle_api_delete(self):
        srv = self.server_instance
        path = self.path.split("?")[0]
        if path.startswith("/api/sessions/"):
            sid = path.split("/")[3]
            if srv and srv.session_provider:
                srv.session_provider.delete_session(sid)
            self._json_response({"ok": True})
        else:
            self._json_response({"ok": False, "error": "Unknown endpoint"}, 404)


def _serialize_session(s):
    return {
        "id": getattr(s, "id", str(s)),
        "title": s.get_display_title() if hasattr(s, "get_display_title") else getattr(s, "title", "New Session"),
        "status": getattr(s, "status", "idle"),
        "messages": [{"role": m.get("role", "system"), "content": m.get("content", "")}
                     for m in getattr(s, "messages", [])],
    }


def _find_free_port(start=8765, end=8800):
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError("No free port found")


class ChatbotServer:
    """Host the chatbot HTML blueprint as a local web server.

    Args:
        title: Display title for the chatbot
        port: HTTP server port (auto-selects if 0)
        ws_port: WebSocket port (auto-selects if 0)
        on_send: Callback(session_id, text) when user sends a message
        session_provider: Object implementing session CRUD interface
    """

    def __init__(
        self,
        title: str = "OPENCLAW",
        port: int = 0,
        ws_port: int = 0,
        on_send: Optional[Callable] = None,
        session_provider: Any = None,
    ):
        self.title = title
        self.port = port or _find_free_port(8080, 8200)
        self.ws_port = ws_port or _find_free_port(8765, 8900)
        self.on_send = on_send
        self.session_provider = session_provider
        self._pipeline_running = False
        self._http_server = None
        self._ws_clients = set()
        self._thread = None
        self._ws_thread = None
        self._running = False
        self._ws_loop = None

    def start(self):
        """Start HTTP and WebSocket servers in background threads."""
        self._running = True

        _StaticHandler.server_instance = self
        self._http_server = HTTPServer(("127.0.0.1", self.port), _StaticHandler)
        self._thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._thread.start()

        self._ws_thread = threading.Thread(target=self._run_ws, daemon=True)
        self._ws_thread.start()

        log.info("Chatbot server started at http://localhost:%d (WS: %d)", self.port, self.ws_port)

    def _run_ws(self):
        """Run the asyncio WebSocket server."""
        try:
            import websockets
        except ImportError:
            log.warning("websockets package not installed — WebSocket disabled, using HTTP polling")
            return

        async def handler(websocket, path=None):
            self._ws_clients.add(websocket)
            try:
                sessions = self.session_provider.list_sessions() if self.session_provider else []
                await websocket.send(json.dumps({
                    "type": "sessions",
                    "sessions": [_serialize_session(s) for s in sessions],
                }))
                async for raw in websocket:
                    try:
                        msg = json.loads(raw)
                        await self._handle_ws_message(websocket, msg)
                    except json.JSONDecodeError:
                        pass
            except Exception:
                pass
            finally:
                self._ws_clients.discard(websocket)

        self._ws_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._ws_loop)

        async def serve():
            async with websockets.serve(handler, "127.0.0.1", self.ws_port):
                while self._running:
                    await asyncio.sleep(0.5)

        self._ws_loop.run_until_complete(serve())

    async def _handle_ws_message(self, ws, msg):
        msg_type = msg.get("type")

        if msg_type == "create_session" and self.session_provider:
            s = self.session_provider.create_session()
            await self._broadcast({
                "type": "session_created",
                "session": _serialize_session(s),
            })

        elif msg_type == "send_message":
            sid = msg.get("session_id")
            text = msg.get("text", "")
            if sid and text and self.on_send:
                self.on_send(sid, text)

        elif msg_type == "delete_session" and self.session_provider:
            sid = msg.get("session_id")
            if sid:
                self.session_provider.delete_session(sid)
                sessions = self.session_provider.list_sessions()
                await self._broadcast({
                    "type": "sessions",
                    "sessions": [_serialize_session(s) for s in sessions],
                })

        elif msg_type == "stop_pipeline":
            self._pipeline_running = False
            await self._broadcast({"type": "pipeline_status", "running": False})

    async def _broadcast(self, data):
        raw = json.dumps(data)
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send(raw)
            except Exception:
                dead.add(ws)
        self._ws_clients -= dead

    def broadcast_sync(self, data: dict):
        """Thread-safe broadcast to all WebSocket clients."""
        if not self._ws_loop or not self._ws_clients:
            return
        asyncio.run_coroutine_threadsafe(self._broadcast(data), self._ws_loop)

    # --- External control API (mirrors tkinter chatbot blueprint) ---

    def send_message_to_gui(self, session_id: str, role: str, content: str):
        """Push a message to the GUI (called from pipeline/backend threads)."""
        if self.session_provider:
            self.session_provider.add_message(session_id, role, content)
        self.broadcast_sync({
            "type": "message",
            "session_id": session_id,
            "role": role,
            "content": content,
        })

    def update_session_title(self, session_id: str, title: str):
        """Update a session's title in the GUI."""
        if self.session_provider:
            self.session_provider.update_title(session_id, title)
        self.broadcast_sync({
            "type": "title_update",
            "session_id": session_id,
            "title": title,
        })

    def set_pipeline_running(self, running: bool):
        """Update pipeline status in the GUI."""
        self._pipeline_running = running
        self.broadcast_sync({"type": "pipeline_status", "running": running})

    def set_typing(self, active: bool):
        """Show/hide typing indicator."""
        self.broadcast_sync({"type": "typing", "active": active})

    def set_status(self, text: str):
        """Update status badge text."""
        self.broadcast_sync({"type": "status", "text": text})

    def open_browser(self):
        """Open the chatbot in Chrome via CDMCP or fall back to webbrowser."""
        url = f"http://localhost:{self.port}/"
        opened = False
        try:
            from logic.chrome.session import open_tab, CDP_PORT
            opened = open_tab(url, port=CDP_PORT)
        except Exception:
            pass
        if not opened:
            import webbrowser
            webbrowser.open(url)

    def stop(self):
        """Stop both HTTP and WebSocket servers."""
        self._running = False
        if self._http_server:
            self._http_server.shutdown()

    def wait(self):
        """Block until server stops."""
        if self._thread:
            self._thread.join()
