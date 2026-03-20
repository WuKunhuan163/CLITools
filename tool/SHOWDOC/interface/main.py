"""SHOWDOC Tool Interface -- ShowDoc via Chrome CDP."""
from tool.SHOWDOC.logic.utils.chrome.api import (  # noqa: F401
    # Session
    boot_session,
    get_session_status,
    # Auth
    get_auth_state,
    get_user_info,
    # Read
    get_page_state,
    get_projects,
    get_project_info,
    get_project_groups,
    get_catalog,
    get_page_content,
    get_unread_messages,
    search_project,
    # Write
    create_project,
    update_project,
    delete_project,
    star_project,
    unstar_project,
    save_page,
    delete_page,
    get_page_history,
    create_catalog,
    rename_catalog,
    delete_catalog,
    # Navigation
    navigate_home,
    navigate_to_project,
    navigate_to_page,
    # Visual
    take_screenshot,
)
