"""MCP configuration for KLING."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for KLING."""
    return MCPToolConfig(
        tool_name="KLING",
        mcp_server="mcp-kling",
        mcp_package="mcp-kling",
        package_type="npm",
        capabilities=['text-to-video', 'image-to-video', 'lip-sync', 'image-generation', 'virtual-try-on'],
        required_env=['KLING_ACCESS_KEY', 'KLING_SECRET_KEY'],
    )
