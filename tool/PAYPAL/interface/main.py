"""PAYPAL Tool Interface — PayPal via Chrome CDP."""
from tool.PAYPAL.logic.utils.chrome.api import (  # noqa: F401
    find_paypal_tab,
    get_auth_state,
    get_page_info,
    get_account_info,
    get_recent_activity,
)
