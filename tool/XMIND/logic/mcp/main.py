"""MCP configuration for XMIND."""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for XMIND."""
    return MCPToolConfig(
        tool_name="XMIND",
        mcp_server="mcp-xmind",
        mcp_package="mcp-xmind",
        package_type="npm",
        capabilities=['create-mindmap', 'export-mindmap', 'edit-mindmap'],
        required_env=[],
    )
