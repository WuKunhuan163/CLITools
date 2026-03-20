"""Tool base and setup interface.

Provides the core tool infrastructure classes.
IDE functions delegate to tool/IDE/interface/ for detection and deployment.
"""
from logic.tool.blueprint.base import ToolBase
from logic._.setup.engine import ToolEngine
from logic._.setup.userinput.prompts import get_default_prompts
from logic.tool.blueprint.mcp import MCPToolBase

from tool.IDE.interface.main import detect_cursor as detect_cursor_ide
from tool.IDE.interface.main import deploy_cursor
from tool.IDE.interface.main import detect_ides as detect_ai_ides

__all__ = [
    "ToolBase",
    "MCPToolBase",
    "ToolEngine",
    "get_default_prompts",
    "detect_cursor_ide",
    "deploy_cursor",
    "detect_ai_ides",
]
