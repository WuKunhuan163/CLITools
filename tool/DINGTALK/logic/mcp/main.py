"""MCP configuration for DINGTALK."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for DINGTALK."""
    return MCPToolConfig(
        tool_name="DINGTALK",
        mcp_server="mcp-dingtalk",
        mcp_package="mcp-dingtalk",
        package_type="npm",
        capabilities=['send-message', 'create-group', 'manage-tasks'],
        required_env=['DINGTALK_APP_KEY', 'DINGTALK_APP_SECRET'],
    )
