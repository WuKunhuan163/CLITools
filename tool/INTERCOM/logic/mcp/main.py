"""MCP configuration for INTERCOM."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for INTERCOM."""
    return MCPToolConfig(
        tool_name="INTERCOM",
        mcp_server="mcp-intercom",
        mcp_package="mcp-intercom",
        package_type="npm",
        capabilities=['manage-contacts', 'send-messages', 'track-events'],
        required_env=['INTERCOM_ACCESS_TOKEN'],
    )
