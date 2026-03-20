"""SHIM — Tool blueprints have moved to __/interface/.

This file re-exports for backward compatibility during migration.
"""
# TODO: Remove this shim after all imports are migrated to interface.base
from __.interface.base import ToolBase  # noqa: F401
from __.interface.mcp import MCPToolBase  # noqa: F401

__all__ = ["ToolBase", "MCPToolBase"]
