"""MCP (Model Context Protocol) infrastructure for AITerminalTools."""
from logic.mcp.config import is_cursor_environment, get_available_mcp_servers
from logic.mcp.browser import BrowserMCPConfig

__all__ = [
    "is_cursor_environment",
    "get_available_mcp_servers",
    "BrowserMCPConfig",
]
