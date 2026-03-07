"""Shared local HTML server for serving tool dashboards and UIs.

Provides a reusable HTTP server that serves a single HTML file (or a
directory of static assets) on localhost. Designed to be used by any
tool that needs a persistent local web UI (LLM dashboard, OPENCLAW HTML
GUI, CDMCP session page, etc.).

Usage:
    from logic.serve.html_server import LocalHTMLServer

    server = LocalHTMLServer(
        html_path="/path/to/dashboard.html",
        port=0,           # auto-select
        title="LLM Dashboard",
    )
    server.start()          # non-blocking background thread
    server.open_browser()   # opens in Chrome or default browser
    server.wait()           # block until killed
"""
import json
import os
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Callable, Optional

_RUN_DIR = Path("/Applications/AITerminalTools/data/serve")


def find_free_port(start: int = 8100, end: int = 8300) -> int:
    """Find a free TCP port in the given range.

    Parameters
    ----------
    start : int
        First port to try.
    end : int
        Last port to try (exclusive).

    Returns
    -------
    int
        A free port number.

    Raises
    ------
    RuntimeError
        If no free port is found in the range.
    """
    for port in range(start, end):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    raise RuntimeError(f"No free port in range {start}-{end}")


class _SingleFileHandler(SimpleHTTPRequestHandler):
    """Serve a single HTML file for GET / and static files from its directory."""

    _html_path: Optional[Path] = None
    _api_handler: Optional[Callable] = None

    def __init__(self, *args, **kwargs):
        directory = str(self._html_path.parent) if self._html_path else "."
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/health":
            self._json_response({"ok": True})
        elif path.startswith("/api/") and self._api_handler:
            result = self._api_handler("GET", path, None)
            self._json_response(result)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") and self._api_handler:
            body = self._read_body()
            result = self._api_handler("POST", self.path, body)
            self._json_response(result)
        else:
            self.send_error(404)

    def _serve_html(self):
        if not self._html_path or not self._html_path.exists():
            self.send_error(404)
            return
        data = self._html_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data)

    def _json_response(self, data, status=200):
        body = json.dumps(data, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}


class LocalHTMLServer:
    """Persistent local HTTP server for HTML dashboards and UIs.

    Parameters
    ----------
    html_path : str or Path
        Path to the HTML file to serve at ``/``.
    port : int
        TCP port. Pass 0 to auto-select a free port.
    title : str
        Human-readable name (used in state file and logs).
    api_handler : callable, optional
        ``(method, path, body) -> dict`` for ``/api/*`` routes.
    on_generate : callable, optional
        Called before each ``GET /`` to regenerate the HTML (e.g., refresh
        dashboard data). Receives ``html_path`` as argument.
    """

    def __init__(
        self,
        html_path: str,
        port: int = 0,
        title: str = "HTML Server",
        api_handler: Optional[Callable] = None,
        on_generate: Optional[Callable] = None,
    ):
        self.html_path = Path(html_path)
        self.port = port or find_free_port()
        self.title = title
        self.api_handler = api_handler
        self.on_generate = on_generate
        self._httpd: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._pid = os.getpid()
        self._state_file = _RUN_DIR / f"{title.lower().replace(' ', '_')}_{self._pid}.json"

    def _write_state(self):
        _RUN_DIR.mkdir(parents=True, exist_ok=True)
        state = {
            "pid": self._pid,
            "port": self.port,
            "title": self.title,
            "html_path": str(self.html_path),
            "url": f"http://localhost:{self.port}/",
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        try:
            self._state_file.write_text(json.dumps(state, ensure_ascii=False))
        except Exception:
            pass

    def _cleanup_state(self):
        try:
            self._state_file.unlink(missing_ok=True)
        except Exception:
            pass

    def start(self):
        """Start the HTTP server in a background thread."""
        if self._running:
            return

        if self.on_generate:
            self.on_generate(str(self.html_path))

        handler_class = type(
            "_Handler", (_SingleFileHandler,),
            {"_html_path": self.html_path, "_api_handler": self.api_handler},
        )
        self._httpd = HTTPServer(("127.0.0.1", self.port), handler_class)
        self._running = True
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self._write_state()

    def stop(self):
        """Stop the server."""
        self._running = False
        if self._httpd:
            self._httpd.shutdown()
        self._cleanup_state()

    def open_browser(self, auto_boot: bool = False):
        """Open the served page in Chrome or default browser.

        Parameters
        ----------
        auto_boot : bool
            If True, boot Chrome automatically if not running (via
            ``auto_acquire_tab``). If False, only open in an already
            running Chrome, falling back to default browser.
        """
        url = f"http://localhost:{self.port}/"
        opened = False
        try:
            if auto_boot:
                from logic.chrome.session import auto_acquire_tab, CDP_PORT
                opened = auto_acquire_tab(url, port=CDP_PORT)
            else:
                from logic.chrome.session import open_tab, CDP_PORT
                opened = open_tab(url, port=CDP_PORT)
        except Exception:
            pass
        if not opened:
            import webbrowser
            webbrowser.open(url)

    @property
    def url(self) -> str:
        return f"http://localhost:{self.port}/"

    def wait(self):
        """Block until the server stops (Ctrl+C or .stop())."""
        if self._thread:
            try:
                self._thread.join()
            except KeyboardInterrupt:
                self.stop()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


def list_running_servers() -> list:
    """List all running LocalHTMLServer instances by reading state files.

    Returns
    -------
    list[dict]
        Each dict has: pid, port, title, url, html_path, started_at.
        Only includes servers whose PID is still alive.
    """
    if not _RUN_DIR.exists():
        return []
    servers = []
    for f in _RUN_DIR.glob("*.json"):
        try:
            state = json.loads(f.read_text())
            pid = state.get("pid", 0)
            if pid and _is_alive(pid):
                servers.append(state)
            else:
                f.unlink(missing_ok=True)
        except Exception:
            pass
    return servers


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False
