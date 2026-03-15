"""MCP configuration for ATLASSIAN."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for ATLASSIAN."""
    return MCPToolConfig(
        tool_name="ATLASSIAN",
        mcp_server="mcp-atlassian",
        mcp_package="mcp-atlassian",
        package_type="npm",
        capabilities=['jira-issues', 'confluence-pages', 'manage-projects'],
        required_env=['ATLASSIAN_API_TOKEN', 'ATLASSIAN_EMAIL'],
    )
