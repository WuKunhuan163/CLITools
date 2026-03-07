"""ATLASSIAN Tool Interface — Atlassian account info via Chrome CDP.

Exposes Atlassian functions for other tools to import::

    from tool.ATLASSIAN.logic.interface.main import (
        find_atlassian_tab,
        get_me,
        get_notifications,
    )
"""
from tool.ATLASSIAN.logic.chrome.api import (  # noqa: F401
    find_atlassian_tab,
    get_me,
    get_notifications,
    get_user_preferences,
)
