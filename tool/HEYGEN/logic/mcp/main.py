"""MCP configuration for HEYGEN."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for HEYGEN."""
    return MCPToolConfig(
        tool_name="HEYGEN",
        mcp_server="mcp-heygen",
        mcp_package="mcp-heygen",
        package_type="npm",
        capabilities=['avatar-video', 'text-to-speech', 'video-translate'],
        required_env=['HEYGEN_API_KEY'],
    )
