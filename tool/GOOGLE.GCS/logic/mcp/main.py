"""MCP configuration for GOOGLE.GCS.

GCS uses the cursor-ide-browser MCP for:
- Opening Colab notebooks in the integrated browser
- Creating notebooks via Drive UI when API upload fails
- Interactive Colab session management
"""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from logic.mcp.config import MCPToolConfig
from logic.mcp.browser import BrowserMCPConfig


def get_mcp_config():
    """Return the MCP configuration for GCS."""
    return MCPToolConfig(
        tool_name="GOOGLE.GCS",
        mcp_server="cursor-ide-browser",
        mcp_package=None,
        package_type="built-in",
        capabilities=["colab-notebook", "drive-ui", "browser-automation"],
        required_env=[],
    )


def is_browser_ready():
    """Check if browser MCP is available for GCS operations."""
    return BrowserMCPConfig.is_available()


def get_colab_url(file_id):
    """Generate Colab URL from a Drive file ID."""
    return BrowserMCPConfig.colab_url(file_id)


def get_drive_folder_url(folder_id):
    """Generate Drive folder URL."""
    return BrowserMCPConfig.drive_folder_url(folder_id)
