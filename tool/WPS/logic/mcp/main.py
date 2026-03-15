"""MCP configuration for WPS."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for WPS."""
    return MCPToolConfig(
        tool_name="WPS",
        mcp_server="mcp-wps",
        mcp_package="mcp-wps",
        package_type="npm",
        capabilities=['create-document', 'edit-spreadsheet', 'manage-files'],
        required_env=['WPS_API_KEY'],
    )
