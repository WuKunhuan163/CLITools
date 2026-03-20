"""MCP configuration for DINGTALK.

Uses the DingTalk Open Platform REST API - no external npm packages needed.
"""
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from interface.mcp import MCPToolConfig


def get_mcp_config():
    """Return the MCP configuration for DINGTALK."""
    return MCPToolConfig(
        tool_name="DINGTALK",
        mcp_server="dingtalk-api",
        mcp_package=None,
        package_type="builtin",
        capabilities=[
            "send-message",
            "send-group-message",
            "webhook-message",
            "work-notification",
            "contact-lookup",
            "create-todo",
        ],
        required_env=["DINGTALK_APP_KEY", "DINGTALK_APP_SECRET"],
    )
