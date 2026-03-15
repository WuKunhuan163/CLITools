"""MCP configuration for GITLAB."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for GITLAB."""
    return MCPToolConfig(
        tool_name="GITLAB",
        mcp_server="mcp-gitlab",
        mcp_package="mcp-gitlab",
        package_type="npm",
        capabilities=['manage-repos', 'create-issues', 'ci-cd'],
        required_env=['GITLAB_TOKEN'],
    )
