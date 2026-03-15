"""MCP configuration for PAYPAL."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for PAYPAL."""
    return MCPToolConfig(
        tool_name="PAYPAL",
        mcp_server="mcp-paypal",
        mcp_package="mcp-paypal",
        package_type="npm",
        capabilities=['create-payment', 'manage-orders', 'refund'],
        required_env=['PAYPAL_CLIENT_ID', 'PAYPAL_SECRET'],
    )
