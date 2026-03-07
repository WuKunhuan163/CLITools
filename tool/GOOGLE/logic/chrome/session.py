"""Core CDP session management — backward-compatibility re-export.

All generic Chrome CDP functionality has been extracted to the shared
``logic.chrome.session`` module.  This file re-exports everything so
existing ``from tool.GOOGLE.logic.chrome.session import ...`` continues
to work without changes.
"""
from logic.chrome.session import (  # noqa: F401
    CDP_PORT,
    CDP_TIMEOUT,
    CDPSession,
    is_chrome_cdp_available,
    list_tabs,
    find_tab,
    close_tab,
    open_tab,
    real_click,
    insert_text,
    dispatch_key,
    capture_screenshot,
    get_dom_text,
    get_dom_attribute,
    query_selector_all_text,
    fetch_api,
)
