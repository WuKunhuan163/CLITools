"""MCP configuration for WHATSAPP."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for WHATSAPP."""
    return MCPToolConfig(
        tool_name="WHATSAPP",
        mcp_server="mcp-whatsapp",
        mcp_package="mcp-whatsapp",
        package_type="npm",
        capabilities=['send-message', 'send-media', 'manage-contacts'],
        required_env=['WHATSAPP_TOKEN'],
    )
