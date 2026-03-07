"""Browser MCP configuration and workflow helpers.

The cursor-ide-browser MCP enables browser automation for tools that need
web-based interaction (e.g., Google Colab, Drive UI operations).

This module provides configuration and common patterns. Actual browser
tool calls are made by the AI agent through MCP tool invocations.
"""
from logic.mcp.config import is_cursor_environment, is_browser_mcp_available


class BrowserMCPConfig:
    """Configuration and availability for browser-based MCP operations."""

    SERVER_NAME = "cursor-ide-browser"

    KNOWN_TOOLS = [
        "browser_navigate", "browser_snapshot", "browser_click",
        "browser_type", "browser_fill", "browser_press_key",
        "browser_tabs", "browser_lock", "browser_unlock",
        "browser_wait_for", "browser_scroll", "browser_hover",
        "browser_take_screenshot", "browser_search",
        "browser_handle_dialog", "browser_get_attribute",
        "browser_network_requests", "browser_console_messages",
    ]

    @classmethod
    def is_available(cls):
        """Check if browser MCP is available in the current environment."""
        if not is_cursor_environment():
            return False
        return is_browser_mcp_available()

    @classmethod
    def get_status(cls):
        """Return a status dict for the browser MCP."""
        cursor = is_cursor_environment()
        browser = is_browser_mcp_available() if cursor else False
        return {
            "server": cls.SERVER_NAME,
            "cursor_detected": cursor,
            "browser_available": browser,
            "ready": cursor and browser,
        }

    @classmethod
    def colab_url(cls, file_id):
        """Generate a Colab URL from a Drive file ID."""
        return f"https://colab.research.google.com/drive/{file_id}"

    @classmethod
    def drive_folder_url(cls, folder_id):
        """Generate a Google Drive folder URL."""
        return f"https://drive.google.com/drive/folders/{folder_id}"
