"""Base tool infrastructure interface.

Public facade for the project's foundational base classes.
Canonical source: __/interface/

All tools should inherit from these base classes through this module:
    from interface.base import ToolBase
    from interface.base import MCPToolBase
    from interface.base import CliEndpoint
"""
from __.interface.base import ToolBase
from __.interface.mcp import MCPToolBase
from __.interface.cli import CliEndpoint

__all__ = ["ToolBase", "MCPToolBase", "CliEndpoint"]
