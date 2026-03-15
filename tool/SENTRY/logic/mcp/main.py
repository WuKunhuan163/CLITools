"""MCP configuration for SENTRY."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for SENTRY."""
    return MCPToolConfig(
        tool_name="SENTRY",
        mcp_server="mcp-sentry",
        mcp_package="mcp-sentry",
        package_type="npm",
        capabilities=['track-errors', 'manage-issues', 'performance'],
        required_env=['SENTRY_AUTH_TOKEN'],
    )
