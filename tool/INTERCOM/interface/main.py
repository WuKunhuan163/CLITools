"""INTERCOM Tool Interface — Intercom via Chrome CDP.

Exposes Intercom functions for other tools::

    from tool.INTERCOM.interface.main import (
        find_intercom_tab,
        get_auth_state,
        get_page_info,
    )
"""
from tool.INTERCOM.logic.chrome.api import (  # noqa: F401
    find_intercom_tab,
    get_auth_state,
    get_page_info,
    get_conversations,
    get_contacts,
)
