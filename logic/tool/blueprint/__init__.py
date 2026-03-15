"""Tool blueprints: base classes for different tool archetypes."""
from logic.tool.blueprint.base import ToolBase
from logic.tool.blueprint.mcp import MCPToolBase

__all__ = ["ToolBase", "MCPToolBase"]
