"""CDMCP Local HTTP Server — Persistent background server with auth API.

Starts a standalone HTTP server process that survives the parent process.
Serves the welcome page, chat app, and Google auth API. State is persisted
to a file so any process can discover the running server.
"""

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

_TOOL_DIR = Path(__file__).resolve().parent.parent.parent
_PROJECT_ROOT = _TOOL_DIR.parent.parent
_STANDALONE_SCRIPT = _TOOL_DIR / "logic" / "cdp" / "server_standalone.py"
_STATE_FILE = _TOOL_DIR / "data" / "sessions" / "server_state.json"
_IDENTITY_FILE = _TOOL_DIR / "data" / "sessions" / "google_identity.json"

_server_port: Optional[int] = None


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _find_python() -> str:
    """Find the project's Python with dependencies installed."""
    tool_json = _PROJECT_ROOT / "tool" / "PYTHON" / "tool.json"
    if tool_json.exists():
        try:
            with open(tool_json) as f:
                cfg = json.load(f)
            ver = cfg.get("default_version", "")
            if ver:
                candidate = (_PROJECT_ROOT / "tool" / "PYTHON" / "data" /
                             "install" / ver / "install" / "bin" / "python3")
                if candidate.exists():
                    return str(candidate)
        except Exception:
            pass
    return sys.executable


def _read_state() -> Optional[dict]:
    """Read the server state file (pid + port)."""
    try:
        if _STATE_FILE.exists():
            with open(_STATE_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return None


def _is_server_alive(port: int) -> bool:
    """Health check the server via its /health endpoint."""
    try:
        url = f"http://127.0.0.1:{port}/health"
        with urllib.request.urlopen(url, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            return data.get("ok", False)
    except Exception:
        return False


def _is_pid_alive(pid: int) -> bool:
    """Check if a process with given PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def set_identity_cache(email: str, display_name: str = None):
    """Persist identity to a shared file."""
    _IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_IDENTITY_FILE, "w") as f:
            json.dump({"email": email, "display_name": display_name}, f)
    except OSError:
        pass


def start_server(preferred_port: Optional[int] = None) -> Tuple[str, int]:
    """Start or connect to the persistent HTTP server. Returns (url, port).

    1. If a server is already running (state file + health check), reuse it.
    2. If preferred_port is given, try to use it.
    3. Otherwise, find a free port and start a new standalone process.
    """
    global _server_port

    # Check if already connected in this process
    if _server_port and _is_server_alive(_server_port):
        return f"http://127.0.0.1:{_server_port}", _server_port

    # Check if a persistent server is already running
    state = _read_state()
    if state:
        port = state.get("port")
        pid = state.get("pid")
        if port and _is_server_alive(port):
            _server_port = port
            return f"http://127.0.0.1:{port}", port
        # Stale state; kill the old process if it's still around
        if pid and _is_pid_alive(pid):
            try:
                os.kill(pid, 15)
            except Exception:
                pass

    # Check if preferred_port is already serving
    if preferred_port and _is_server_alive(preferred_port):
        _server_port = preferred_port
        return f"http://127.0.0.1:{preferred_port}", preferred_port

    # Start a new standalone server process
    port = preferred_port or _find_free_port()
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

    py = _find_python()
    log_dir = _TOOL_DIR / "data" / "report"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "server.log"

    with open(log_file, "a") as lf:
        subprocess.Popen(
            [py, str(_STANDALONE_SCRIPT), str(port),
             "--state-file", str(_STATE_FILE)],
            stdout=lf,
            stderr=lf,
            start_new_session=True,
        )

    # Wait for the server to be ready
    for _ in range(20):
        time.sleep(0.25)
        if _is_server_alive(port):
            _server_port = port
            return f"http://127.0.0.1:{port}", port

    # Fallback: check state file
    state = _read_state()
    if state and state.get("port"):
        port = state["port"]
        _server_port = port
        return f"http://127.0.0.1:{port}", port

    raise RuntimeError(f"Failed to start CDMCP server on port {port}")


def stop_server():
    """Stop the persistent server process."""
    global _server_port
    state = _read_state()
    if state:
        pid = state.get("pid")
        if pid and _is_pid_alive(pid):
            try:
                os.kill(pid, 15)
            except Exception:
                pass
    try:
        if _STATE_FILE.exists():
            _STATE_FILE.unlink()
    except OSError:
        pass
    _server_port = None


def get_server_url() -> Optional[str]:
    """Return the server URL if running."""
    global _server_port
    if _server_port and _is_server_alive(_server_port):
        return f"http://127.0.0.1:{_server_port}"
    state = _read_state()
    if state and _is_server_alive(state.get("port", 0)):
        _server_port = state["port"]
        return f"http://127.0.0.1:{_server_port}"
    return None


def is_running() -> bool:
    """Check if the server is alive."""
    return get_server_url() is not None
