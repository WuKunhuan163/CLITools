"""Chrome CDP session interface.

Provides all Chrome DevTools Protocol utilities for browser automation.
"""
from logic.chrome.session import (
    CDP_PORT,
    CDPSession,
    is_chrome_cdp_available,
    list_tabs,
    find_tab,
    close_tab,
    open_tab,
    auto_acquire_tab,
    real_click,
    insert_text,
    dispatch_key,
    capture_screenshot,
    get_dom_text,
    get_dom_attribute,
    query_selector_all_text,
    fetch_api,
)

__all__ = [
    "CDP_PORT",
    "CDPSession",
    "is_chrome_cdp_available",
    "list_tabs",
    "find_tab",
    "close_tab",
    "open_tab",
    "auto_acquire_tab",
    "real_click",
    "insert_text",
    "dispatch_key",
    "capture_screenshot",
    "get_dom_text",
    "get_dom_attribute",
    "query_selector_all_text",
    "fetch_api",
]
