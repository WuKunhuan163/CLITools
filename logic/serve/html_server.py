"""Shared local HTML server for serving tool dashboards and UIs.

Provides a reusable HTTP server that serves a single HTML file (or a
directory of static assets) on localhost. Designed to be used by any
tool that needs a persistent local web UI (LLM dashboard, OPENCLAW HTML
GUI, CDMCP session page, etc.).

Supports Server-Sent Events (SSE) for real-time streaming of LLM tokens
and agent protocol events to browser clients.

Usage:
    from logic.serve.html_server import LocalHTMLServer

    server = LocalHTMLServer(
        html_path="/path/to/dashboard.html",
        port=0,           # auto-select
        title="LLM Dashboard",
    )
    server.start()          # non-blocking background thread
    server.open_browser()   # opens in Chrome or default browser

    # Push events to connected browser clients
    server.push_event({"type": "text", "tokens": "Hello"})

    server.wait()           # block until killed
"""
import json
import os
import queue
import socket
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Callable, List, Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RUN_DIR = _PROJECT_ROOT / "data" / "serve"


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


class _SSEBroker:
    """Manages multiple SSE client connections and broadcasts events."""

    def __init__(self):
        self._clients: List[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=256)
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            try:
                self._clients.remove(q)
            except ValueError:
                pass

    def publish(self, data: dict):
        payload = json.dumps(data, default=str)
        with self._lock:
            dead = []
            for q in self._clients:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                try:
                    self._clients.remove(q)
                except ValueError:
                    pass

    @property
    def client_count(self) -> int:
        with self._lock:
            return len(self._clients)


class _SingleFileHandler(SimpleHTTPRequestHandler):
    """Serve a single HTML file for GET / and static files from its directory."""

    _html_path: Optional[Path] = None
    _api_handler: Optional[Callable] = None
    _page_handler: Optional[Callable] = None
    _sse_broker: Optional[_SSEBroker] = None

    def __init__(self, *args, **kwargs):
        directory = str(self._html_path.parent) if self._html_path else "."
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        buf = getattr(self, "_headers_buffer", [])
        has_cache = any(
            "cache-control" in (item.decode("latin-1") if isinstance(item, bytes) else str(item)).lower()
            for item in buf
        )
        if not has_cache:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_html()
        elif path == "/health":
            self._json_response({"ok": True})
        elif path == "/api/events" and self._sse_broker:
            self._serve_sse()
        elif path.startswith("/api/") and self._api_handler:
            result = self._api_handler("GET", path, None)
            self._json_response(result)
        elif path.startswith("/session/") and self._page_handler:
            html = self._page_handler(self.path)
            if html:
                self._html_response(html)
            else:
                self.send_error(404)
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/") and self._api_handler:
            body = self._read_body()
            result = self._api_handler("POST", self.path, body)
            self._json_response(result)
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/") and self._api_handler:
            body = self._read_body()
            result = self._api_handler("DELETE", self.path, body)
            self._json_response(result)
        else:
            self.send_error(404)

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        client_q = self._sse_broker.subscribe()
        try:
            while True:
                try:
                    payload = client_q.get(timeout=15)
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self._sse_broker.unsubscribe(client_q)

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

    def _html_response(self, html: str, status=200):
        body = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
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
        page_handler: Optional[Callable] = None,
        on_generate: Optional[Callable] = None,
        enable_sse: bool = False,
    ):
        self.html_path = Path(html_path)
        self.port = port or find_free_port()
        self.title = title
        self.api_handler = api_handler
        self.page_handler = page_handler
        self.on_generate = on_generate
        self._sse_broker = _SSEBroker() if enable_sse else None
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
            {"_html_path": self.html_path,
             "_api_handler": staticmethod(self.api_handler) if self.api_handler else None,
             "_page_handler": staticmethod(self.page_handler) if self.page_handler else None,
             "_sse_broker": self._sse_broker},
        )
        threaded_server = type("_ThreadedHTTPServer", (ThreadingMixIn, HTTPServer), {"daemon_threads": True, "allow_reuse_address": True})
        self._httpd = threaded_server(("127.0.0.1", self.port), handler_class)
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

    def push_event(self, data: dict):
        """Push a protocol event to all connected SSE clients.

        Parameters
        ----------
        data : dict
            Agent protocol event, e.g. ``{"type": "text", "tokens": "..."}``
            or ``{"type": "tool", "name": "exec", ...}``.

        Raises
        ------
        RuntimeError
            If SSE is not enabled on this server.
        """
        if not self._sse_broker:
            raise RuntimeError("SSE not enabled. Pass enable_sse=True to constructor.")
        self._sse_broker.publish(data)

    @property
    def sse_client_count(self) -> int:
        """Number of currently connected SSE clients."""
        return self._sse_broker.client_count if self._sse_broker else 0

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
