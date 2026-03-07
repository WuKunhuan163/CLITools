"""CDMCP Local HTTP Server — Serves the chat app HTML for demo sessions.

Runs a lightweight HTTP server on a random available port to serve the
self-contained chat app HTML file.
"""

import http.server
import threading
import socket
from pathlib import Path
from typing import Optional, Tuple

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_CHAT_HTML = _TOOL_DIR / "data" / "chat_app.html"
_WELCOME_HTML = _TOOL_DIR / "data" / "welcome.html"

_server_instance: Optional[http.server.HTTPServer] = None
_server_port: Optional[int] = None
_server_thread: Optional[threading.Thread] = None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ChatHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/chat"):
            content = _CHAT_HTML.read_bytes()
        elif path == "/welcome":
            content = _WELCOME_HTML.read_bytes()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        pass


def start_server() -> Tuple[str, int]:
    """Start the local HTTP server and return (url, port)."""
    global _server_instance, _server_port, _server_thread

    if _server_instance and _server_port:
        return f"http://127.0.0.1:{_server_port}", _server_port

    port = _find_free_port()
    server = http.server.HTTPServer(("127.0.0.1", port), _ChatHandler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    _server_instance = server
    _server_port = port
    _server_thread = thread

    return f"http://127.0.0.1:{port}", port


def stop_server():
    global _server_instance, _server_port, _server_thread
    if _server_instance:
        _server_instance.shutdown()
        _server_instance = None
        _server_port = None
        _server_thread = None


def get_server_url() -> Optional[str]:
    if _server_port:
        return f"http://127.0.0.1:{_server_port}"
    return None


def is_running() -> bool:
    return _server_instance is not None
