"""MCP configuration for ASANA."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for ASANA."""
    return MCPToolConfig(
        tool_name="ASANA",
        mcp_server="mcp-asana",
        mcp_package="mcp-asana",
        package_type="npm",
        capabilities=['create-task', 'manage-projects', 'track-progress'],
        required_env=['ASANA_ACCESS_TOKEN'],
    )
