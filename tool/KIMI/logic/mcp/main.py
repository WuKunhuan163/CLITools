"""MCP configuration for KIMI."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for KIMI."""
    return MCPToolConfig(
        tool_name="KIMI",
        mcp_server="mcp-kimi",
        mcp_package="mcp-kimi",
        package_type="npm",
        capabilities=['chat', 'file-analysis', 'web-search'],
        required_env=['KIMI_API_KEY'],
    )
