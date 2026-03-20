"""Shared local HTTP serving utilities.

Provides ``LocalHTMLServer`` for single-file dashboards and
``find_free_port`` for port discovery.  Used by LLM dashboard,
OPENCLAW GUIs, and CDMCP blueprint servers.
"""
from logic._.gui.serve.html_server import LocalHTMLServer, find_free_port, list_running_servers

__all__ = ["LocalHTMLServer", "find_free_port", "list_running_servers"]
