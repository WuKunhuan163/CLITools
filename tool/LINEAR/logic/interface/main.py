"""LINEAR Tool Interface — Linear via Chrome CDP.

Exposes Linear functions for other tools::

    from tool.LINEAR.logic.interface.main import (
        find_linear_tab,
        get_auth_state,
        get_user_info,
    )
"""
from tool.LINEAR.logic.chrome.api import (  # noqa: F401
    find_linear_tab,
    get_auth_state,
    get_user_info,
    get_page_info,
)
