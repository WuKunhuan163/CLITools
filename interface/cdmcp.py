"""CDMCP loader interface.

Provides functions to load CDMCP (Chrome DevTools MCP) modules.
"""
from logic._.utils.chrome.loader import (
    load_cdmcp,
    load_cdmcp_overlay,
    load_cdmcp_sessions,
    load_cdmcp_server,
    load_cdmcp_interact,
    load_cdmcp_demo_state,
)

__all__ = [
    "load_cdmcp",
    "load_cdmcp_overlay",
    "load_cdmcp_sessions",
    "load_cdmcp_server",
    "load_cdmcp_interact",
    "load_cdmcp_demo_state",
]
