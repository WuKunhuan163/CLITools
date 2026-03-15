"""MCP configuration for STRIPE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for STRIPE."""
    return MCPToolConfig(
        tool_name="STRIPE",
        mcp_server="mcp-stripe",
        mcp_package="@anthropic/mcp-stripe",
        package_type="npm",
        capabilities=['create-payment', 'manage-subscriptions', 'refund'],
        required_env=['STRIPE_SECRET_KEY'],
    )
