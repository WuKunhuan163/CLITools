"""MCP configuration for GITHUB."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for GITHUB."""
    return MCPToolConfig(
        tool_name="GITHUB",
        mcp_server="mcp-github",
        mcp_package="@anthropic/mcp-github",
        package_type="npm",
        capabilities=['manage-repos', 'create-issues', 'pull-requests'],
        required_env=['GITHUB_TOKEN'],
    )
