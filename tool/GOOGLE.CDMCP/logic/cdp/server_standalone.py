#!/usr/bin/env python3
"""Standalone CDMCP HTTP server process.

Runs as a persistent background process serving the welcome page, chat app,
and auth API. Writes its PID and port to a state file so other processes
can discover and connect to it.

Usage:
    python3 server_standalone.py <port> [--state-file <path>]
"""

import sys
import os
import json
import signal
import http.server
from pathlib import Path

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _TOOL_DIR.parent.parent

sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(str(_PROJECT_ROOT))

_CHAT_HTML = _TOOL_DIR / "data" / "chat_app.html"
_WELCOME_HTML = _TOOL_DIR / "data" / "welcome.html"
_IDENTITY_FILE = _TOOL_DIR / "data" / "sessions" / "google_identity.json"
_SESSION_STATE_FILE = _TOOL_DIR / "data" / "sessions" / "state.json"
_AUTH_MODULE = None
_SM_LOADED = False

import threading
import queue

_sse_clients: list = []
_sse_lock = threading.Lock()


def push_sse_event(event: dict):
    """Push an event to all connected SSE clients."""
    data = json.dumps(event)
    with _sse_lock:
        dead = []
        for q in _sse_clients:
            try:
                q.put_nowait(data)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_clients.remove(q)


def _get_auth_module():
    global _AUTH_MODULE
    if _AUTH_MODULE is None:
        import importlib.util
        auth_path = _TOOL_DIR / "logic" / "cdp" / "google_auth.py"
        spec = importlib.util.spec_from_file_location("cdmcp_auth_srv", str(auth_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _AUTH_MODULE = mod
    return _AUTH_MODULE


def _check_auth() -> dict:
    from interface.chrome import CDPSession, CDP_PORT, list_tabs
    auth = _get_auth_module()
    result = {"signed_in": False, "email": None, "display_name": None}
    try:
        tabs = list_tabs(CDP_PORT)
        for t in tabs:
            ws = t.get("webSocketDebuggerUrl")
            if ws and t.get("type") == "page":
                try:
                    cdp = CDPSession(ws, timeout=3)
                    cookie_result = auth.check_auth_cookies(cdp)
                    result["signed_in"] = cookie_result["signed_in"]
                    cdp.close()
                    if result["signed_in"]:
                        break
                except Exception:
                    continue
    except Exception:
        pass

    if result["signed_in"]:
        try:
            if _IDENTITY_FILE.exists():
                with open(_IDENTITY_FILE) as f:
                    identity = json.load(f)
                if identity.get("email"):
                    result["email"] = identity["email"]
                    result["display_name"] = identity.get("display_name")
        except Exception:
            pass
    else:
        try:
            if _IDENTITY_FILE.exists():
                _IDENTITY_FILE.unlink()
        except OSError:
            pass

    result["touch"] = True
    return result


def _load_session_manager():
    """Ensure session manager module is loaded (for live session access)."""
    global _SM_LOADED
    if _SM_LOADED:
        return
    try:
        import importlib.util
        sm_path = _TOOL_DIR / "logic" / "cdp" / "session_manager.py"
        spec = importlib.util.spec_from_file_location("cdmcp_sm_srv", str(sm_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _SM_LOADED = True
    except Exception:
        pass


def _get_session_info(sid: str) -> dict:
    """Get session info by session_id (prefix match). Reads from state file."""
    try:
        if not _SESSION_STATE_FILE.exists():
            return None
        with open(_SESSION_STATE_FILE) as f:
            state = json.load(f)
        sessions = state.get("sessions", {})
        if not sessions and "_config" not in state:
            sessions = state
        for name, info in sessions.items():
            stored_sid = info.get("session_id", "")
            if stored_sid == sid or stored_sid.startswith(sid) or sid.startswith(stored_sid):
                import time
                now = time.time()
                created = info.get("created_at", now)
                last_act = info.get("last_activity", now)
                timeout = info.get("timeout_sec", 86400)
                idle_timeout = info.get("idle_timeout_sec", 3600)
                return {
                    "ok": True,
                    "name": name,
                    "session_id": stored_sid,
                    "port": info.get("port", 9222),
                    "timeout_sec": timeout,
                    "idle_timeout_sec": idle_timeout,
                    "created_at": int(created),
                    "last_activity": int(last_act),
                    "window_id": info.get("window_id"),
                    "tabs": info.get("tabs", {}),
                    "http_port": info.get("http_port"),
                    "age_sec": int(now - created),
                    "idle_sec": int(now - last_act),
                }
    except Exception:
        pass
    return None


class CDMCPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        query = self.path.split("?")[1] if "?" in self.path else ""

        if path in ("/", "/index.html", "/chat"):
            content = _CHAT_HTML.read_bytes()
        elif path == "/welcome":
            content = _WELCOME_HTML.read_bytes()
        elif path == "/auth":
            self._handle_auth()
            return
        elif path == "/health":
            self._json_response({"ok": True})
            return
        elif path == "/api/events":
            self._handle_sse()
            return
        elif path.startswith("/api/session/"):
            self._handle_session_api(path, query)
            return
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _json_response(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _handle_session_api(self, path, query):
        """Return session metadata as JSON: /api/session/<sid>"""
        parts = path.rstrip("/").split("/")
        sid = parts[3] if len(parts) >= 4 else ""
        if not sid:
            self._json_response({"ok": False, "error": "Missing session_id"}, 400)
            return
        try:
            _load_session_manager()
            info = _get_session_info(sid)
            if info:
                self._json_response(info)
            else:
                self._json_response({"ok": False, "error": f"Session '{sid}' not found"}, 404)
        except Exception as e:
            self._json_response({"ok": False, "error": str(e)}, 500)

    def _handle_sse(self):
        """SSE endpoint: /api/events — real-time state change stream."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        client_queue = queue.Queue(maxsize=50)
        with _sse_lock:
            _sse_clients.append(client_queue)

        try:
            self.wfile.write(b"data: {\"type\":\"connected\"}\n\n")
            self.wfile.flush()

            while True:
                try:
                    data = client_queue.get(timeout=30)
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with _sse_lock:
                if client_queue in _sse_clients:
                    _sse_clients.remove(client_queue)

    def do_POST(self):
        path = self.path.split("?")[0]
        content_len = int(self.headers.get("Content-Length", 0))
        body = {}
        if content_len > 0:
            raw = self.rfile.read(content_len)
            try:
                body = json.loads(raw)
            except Exception:
                pass

        if path == "/api/event":
            push_sse_event(body)
            self._json_response({"ok": True})
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_auth(self):
        try:
            result = _check_auth()
        except Exception:
            result = {"signed_in": False, "email": None, "display_name": None}
        self._json_response(result)

    def log_message(self, format, *args):
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Port to listen on")
    parser.add_argument("--state-file", default="",
                        help="Path to write PID+port state")
    args = parser.parse_args()

    class ThreadedServer(http.server.ThreadingHTTPServer):
        daemon_threads = True

    server = ThreadedServer(("127.0.0.1", args.port), CDMCPHandler)

    if args.state_file:
        state_path = Path(args.state_file)
        state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(state_path, "w") as f:
            json.dump({"pid": os.getpid(), "port": args.port}, f)

    def _cleanup(signum, frame):
        server.shutdown()
        if args.state_file:
            try:
                Path(args.state_file).unlink()
            except OSError:
                pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    server.serve_forever()


if __name__ == "__main__":
    main()
