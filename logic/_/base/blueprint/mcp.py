"""SHIM — MCPToolBase has moved to __/interface/mcp.py.

This file re-exports for backward compatibility during migration.
All new code should import from interface.base or __.interface.mcp.
"""
# TODO: Remove this shim after all imports are migrated to interface.base
from __.interface.mcp import MCPToolBase  # noqa: F401
