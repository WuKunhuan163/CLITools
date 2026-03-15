"""MCP configuration for PLAID."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for PLAID."""
    return MCPToolConfig(
        tool_name="PLAID",
        mcp_server="mcp-plaid",
        mcp_package="mcp-plaid",
        package_type="npm",
        capabilities=['link-accounts', 'get-transactions', 'verify-identity'],
        required_env=['PLAID_CLIENT_ID', 'PLAID_SECRET'],
    )
