"""KLING Tool Interface — Kling AI via Chrome CDP.

Exposes Kling functions for other tools::

    from tool.KLING.logic.interface.main import (
        find_kling_tab,
        get_user_info,
        get_points,
    )
"""
from tool.KLING.logic.chrome.api import (  # noqa: F401
    find_kling_tab,
    get_user_info,
    get_points,
    get_page_info,
    get_generation_history,
)
