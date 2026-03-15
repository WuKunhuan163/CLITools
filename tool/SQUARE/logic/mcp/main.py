"""MCP configuration for SQUARE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for SQUARE."""
    return MCPToolConfig(
        tool_name="SQUARE",
        mcp_server="mcp-square",
        mcp_package="mcp-square",
        package_type="npm",
        capabilities=['process-payment', 'manage-inventory', 'catalog'],
        required_env=['SQUARE_ACCESS_TOKEN'],
    )
