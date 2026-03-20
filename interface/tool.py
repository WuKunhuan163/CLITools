"""Tool base and setup interface.

Provides the core tool infrastructure classes.
IDE functions delegate to tool/IDE/interface/ for detection and deployment.
"""
from logic._.base.blueprint.base import ToolBase
from logic._.base.blueprint.mcp import MCPToolBase
from logic._.base.cli import CliEndpoint
from logic._.setup.engine import ToolEngine
from logic._.dev.resource import fetch_resource
from tool.USERINPUT.logic.prompts import get_default_prompts

from tool.IDE.interface.main import detect_cursor as detect_cursor_ide
from tool.IDE.interface.main import deploy_cursor
from tool.IDE.interface.main import detect_ides as detect_ai_ides

__all__ = [
    "ToolBase",
    "MCPToolBase",
    "CliEndpoint",
    "ToolEngine",
    "fetch_resource",
    "get_default_prompts",
    "detect_cursor_ide",
    "deploy_cursor",
    "detect_ai_ides",
]
