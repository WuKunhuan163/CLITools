"""GMAIL Tool Interface — Gmail via Chrome CDP."""
from tool.GMAIL.logic.chrome.api import (  # noqa: F401
    find_gmail_tab,
    get_auth_state,
    get_page_info,
    get_inbox,
    get_labels,
    search_emails,
    send_email,
)
