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
_AUTH_MODULE = None


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
    from logic.chrome.session import CDPSession, CDP_PORT, list_tabs
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


class CDMCPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/", "/index.html", "/chat"):
            content = _CHAT_HTML.read_bytes()
        elif path == "/welcome":
            content = _WELCOME_HTML.read_bytes()
        elif path == "/auth":
            self._handle_auth()
            return
        elif path == "/health":
            body = b'{"ok":true}'
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
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

    def _handle_auth(self):
        try:
            result = _check_auth()
        except Exception:
            result = {"signed_in": False, "email": None, "display_name": None}
        body = json.dumps(result).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("port", type=int, help="Port to listen on")
    parser.add_argument("--state-file", default="",
                        help="Path to write PID+port state")
    args = parser.parse_args()

    server = http.server.HTTPServer(("127.0.0.1", args.port), CDMCPHandler)

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
