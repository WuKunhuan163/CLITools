"""Lifecycle management interface.

Provides tool lifecycle operations: list, install, uninstall, sync.
Utility functions for use by non-command code (e.g. ToolBase, setup engine).
"""
from logic.tool.lifecycle import (
    list_tools,
    install_tool,
    reinstall_tool,
    uninstall_tool,
)

__all__ = [
    "list_tools",
    "install_tool",
    "reinstall_tool",
    "uninstall_tool",
]
