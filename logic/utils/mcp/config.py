"""MCP environment detection and availability checks."""
import os
from pathlib import Path


def is_cursor_environment():
    """Detect if running inside Cursor IDE."""
    indicators = [
        os.environ.get("CURSOR_SESSION_ID"),
        os.environ.get("CURSOR_TRACE_ID"),
        os.environ.get("TERM_PROGRAM") == "cursor",
    ]
    if any(indicators):
        return True

    home = Path.home()
    cursor_dir = home / ".cursor"
    if cursor_dir.is_dir():
        projects = cursor_dir / "projects"
        if projects.is_dir() and any(projects.iterdir()):
            return True
    return False


def get_mcp_descriptors_dir():
    """Get the MCP tool descriptors directory if available."""
    home = Path.home()
    candidates = list((home / ".cursor" / "projects").glob("*/mcps")) if (home / ".cursor" / "projects").is_dir() else []
    if candidates:
        return candidates[0]
    return None


def get_available_mcp_servers():
    """Return list of available MCP server names from the descriptors directory."""
    mcp_dir = get_mcp_descriptors_dir()
    if not mcp_dir or not mcp_dir.is_dir():
        return []
    return [d.name for d in mcp_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]


def is_browser_mcp_available():
    """Check if the cursor-ide-browser MCP is available."""
    servers = get_available_mcp_servers()
    return "cursor-ide-browser" in servers


class MCPToolConfig:
    """Base configuration for an MCP-backed tool."""

    def __init__(self, tool_name, mcp_server, mcp_package=None, package_type="npm",
                 capabilities=None, required_env=None):
        self.tool_name = tool_name
        self.mcp_server = mcp_server
        self.mcp_package = mcp_package
        self.package_type = package_type
        self.capabilities = capabilities or []
        self.required_env = required_env or []

    def is_available(self):
        """Check if the underlying MCP server is reachable."""
        if self.mcp_server:
            return self.mcp_server in get_available_mcp_servers()
        return True

    def check_env(self):
        """Check if required environment variables are set. Returns list of missing vars."""
        missing = []
        for var in self.required_env:
            if not os.environ.get(var):
                missing.append(var)
        return missing

    def to_dict(self):
        return {
            "tool_name": self.tool_name,
            "mcp_server": self.mcp_server,
            "mcp_package": self.mcp_package,
            "package_type": self.package_type,
            "capabilities": self.capabilities,
            "required_env": self.required_env,
            "available": self.is_available(),
        }
