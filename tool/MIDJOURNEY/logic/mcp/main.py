"""MCP configuration for MIDJOURNEY."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for MIDJOURNEY."""
    return MCPToolConfig(
        tool_name="MIDJOURNEY",
        mcp_server="mcp-midjourney",
        mcp_package="@anthropic/mcp-midjourney",
        package_type="npm",
        capabilities=['text-to-image', 'image-variation', 'upscale'],
        required_env=['MIDJOURNEY_API_KEY'],
    )
