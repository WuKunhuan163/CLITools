"""MCP configuration for SUNO."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for SUNO."""
    return MCPToolConfig(
        tool_name="SUNO",
        mcp_server="mcp-suno",
        mcp_package="mcp-suno",
        package_type="npm",
        capabilities=['text-to-music', 'extend-music', 'manage-library'],
        required_env=['SUNO_API_KEY'],
    )
