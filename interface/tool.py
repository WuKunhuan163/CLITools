"""Tool base and setup interface.

Provides the core tool infrastructure classes.
"""
from logic.tool.blueprint.base import ToolBase
from logic.setup.engine import ToolEngine
from logic.setup.userinput.prompts import get_default_prompts
from logic.setup.cursor.deploy import detect_cursor_ide, deploy as deploy_cursor
from logic.tool.blueprint.mcp import MCPToolBase

__all__ = [
    "ToolBase",
    "MCPToolBase",
    "ToolEngine",
    "get_default_prompts",
    "detect_cursor_ide",
    "deploy_cursor",
]
