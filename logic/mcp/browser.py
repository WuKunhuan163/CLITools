"""Browser MCP configuration and workflow helpers.

The cursor-ide-browser MCP enables browser automation for tools that need
web-based interaction (e.g., Google Colab, Drive UI operations).

This module provides configuration and common patterns. Actual browser
tool calls are made by the AI agent through MCP tool invocations.
"""
from logic.mcp.config import is_cursor_environment, is_browser_mcp_available


class BrowserSize:
    """Predefined browser viewport sizes."""

    COMPACT = (800, 600)
    DEFAULT = (1280, 720)
    LARGE = (1920, 1080)
    DRIVE_MENU = (1024, 768)

    @classmethod
    def get_preset(cls, name):
        presets = {
            "compact": cls.COMPACT,
            "default": cls.DEFAULT,
            "large": cls.LARGE,
            "drive_menu": cls.DRIVE_MENU,
        }
        return presets.get(name, cls.DEFAULT)

    @classmethod
    def list_presets(cls):
        return {
            "compact": {"width": 800, "height": 600, "desc": "Compact view for small panels"},
            "default": {"width": 1280, "height": 720, "desc": "Standard viewport"},
            "large": {"width": 1920, "height": 1080, "desc": "Full HD viewport"},
            "drive_menu": {"width": 1024, "height": 768, "desc": "Optimal for Drive context menus"},
        }


def build_resize_args(width=None, height=None, preset=None, view_id=None):
    """Build arguments for the browser_resize MCP tool.

    Args:
        width: Explicit width in pixels.
        height: Explicit height in pixels.
        preset: Name of a BrowserSize preset (overridden by explicit width/height).
        view_id: Target browser tab ID (optional).

    Returns:
        dict suitable for CallMcpTool arguments.
    """
    if preset and not (width and height):
        w, h = BrowserSize.get_preset(preset)
        width = width or w
        height = height or h
    width = width or 1280
    height = height or 720
    args = {"width": width, "height": height}
    if view_id:
        args["viewId"] = view_id
    return args


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
        "browser_resize",
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

    @classmethod
    def resize_args(cls, width=None, height=None, preset=None, view_id=None):
        """Build browser_resize tool arguments."""
        return build_resize_args(width, height, preset, view_id)
