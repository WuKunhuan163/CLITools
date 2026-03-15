"""MCP configuration interface.

Provides MCPToolConfig and environment detection for MCP-backed tools.
"""
from logic.mcp.config import MCPToolConfig, is_cursor_environment, get_mcp_descriptors_dir

__all__ = [
    "MCPToolConfig",
    "is_cursor_environment",
    "get_mcp_descriptors_dir",
]
