"""Public interface for the local HTML serving infrastructure.

Provides shared utilities for any tool that needs to serve HTML locally:
- LocalHTMLServer: simple static file server with optional API routes
- find_free_port: locate an available TCP port
- is_process_alive: check if a PID is running
- list_running_servers: discover all active LocalHTMLServer instances

Usage:
    from logic._.gui.serve.interface import LocalHTMLServer, find_free_port

    server = LocalHTMLServer(html_path="dashboard.html", title="My Dashboard")
    server.start()
    server.open_browser()
"""

from logic._.gui.serve.html_server import (
    LocalHTMLServer,
    find_free_port,
    list_running_servers,
    _is_alive as is_process_alive,
)

__all__ = [
    "LocalHTMLServer",
    "find_free_port",
    "is_process_alive",
    "list_running_servers",
]
