"""MCP configuration interface.

Provides MCPToolConfig and environment detection for MCP-backed tools.
"""
from logic._.utils.mcp.config import MCPToolConfig, is_cursor_environment, get_mcp_descriptors_dir
from logic._.utils.mcp.browser import BrowserMCPConfig, BrowserSize, build_resize_args
from logic._.utils.mcp.drive_create import build_create_workflow, get_supported_types, build_upload_workflow

__all__ = [
    "MCPToolConfig",
    "is_cursor_environment",
    "get_mcp_descriptors_dir",
    "BrowserMCPConfig",
    "BrowserSize",
    "build_resize_args",
    "build_create_workflow",
    "get_supported_types",
    "build_upload_workflow",
]
