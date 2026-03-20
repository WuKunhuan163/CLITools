"""WPS Tool Interface — WPS Office / KDocs via Chrome CDP."""
from tool.WPS.logic.utils.chrome.api import (  # noqa: F401
    find_wps_tab,
    get_auth_state,
    get_page_info,
    get_user_info,
    get_recent_docs,
)
