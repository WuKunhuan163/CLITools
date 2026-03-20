"""Tool base and setup interface.

# TODO: Migrate — this module will be refactored. Base classes now live in
#       interface/base.py (canonical source: __/interface/).
#       Tool-specific re-exports (IDE, USERINPUT) will move to dedicated facades.

Provides the core tool infrastructure classes.
IDE functions delegate to tool/IDE/interface/ for detection and deployment.
"""
# TODO: [migration] This facade will be migrated/rewritten as part of the __/ architecture restructure.
from interface.base import ToolBase, MCPToolBase, CliEndpoint
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
