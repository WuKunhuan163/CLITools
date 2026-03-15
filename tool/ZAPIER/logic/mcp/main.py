"""MCP configuration for ZAPIER."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for ZAPIER."""
    return MCPToolConfig(
        tool_name="ZAPIER",
        mcp_server="mcp-zapier",
        mcp_package="mcp-zapier",
        package_type="npm",
        capabilities=['create-zap', 'trigger-action', 'manage-workflows'],
        required_env=['ZAPIER_API_KEY'],
    )
