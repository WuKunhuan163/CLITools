"""MCP configuration for LINEAR."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for LINEAR."""
    return MCPToolConfig(
        tool_name="LINEAR",
        mcp_server="mcp-linear",
        mcp_package="mcp-linear",
        package_type="npm",
        capabilities=['create-issue', 'manage-projects', 'track-cycles'],
        required_env=['LINEAR_API_KEY'],
    )
