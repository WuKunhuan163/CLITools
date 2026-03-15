"""MCP configuration for CLOUDFLARE."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for CLOUDFLARE."""
    return MCPToolConfig(
        tool_name="CLOUDFLARE",
        mcp_server="mcp-cloudflare",
        mcp_package="@anthropic/mcp-cloudflare",
        package_type="npm",
        capabilities=['manage-dns', 'manage-workers', 'analytics'],
        required_env=['CLOUDFLARE_API_TOKEN'],
    )
