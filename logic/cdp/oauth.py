"""Backward-compatibility shim — re-exports from tool.GOOGLE.logic.chrome.oauth.

All OAuth automation has been refactored into the GOOGLE tool.
"""
from logic.resolve import setup_paths as _setup_paths
_setup_paths(__file__)

from tool.GOOGLE.logic.chrome.oauth import (  # noqa: F401
    handle_oauth_if_needed,
    close_oauth_tabs,
    has_oauth_dialog,
    click_connect_button,
    find_oauth_tab,
)
from tool.GOOGLE.logic.chrome.session import CDPSession, CDP_PORT  # noqa: F401
