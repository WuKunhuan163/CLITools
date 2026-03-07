"""MCP (Model Context Protocol) infrastructure for AITerminalTools."""
from logic.mcp.config import is_cursor_environment, get_available_mcp_servers, MCPToolConfig
from logic.mcp.browser import BrowserMCPConfig, BrowserSize, build_resize_args

__all__ = [
    "is_cursor_environment",
    "get_available_mcp_servers",
    "MCPToolConfig",
    "BrowserMCPConfig",
    "BrowserSize",
    "build_resize_args",
]
