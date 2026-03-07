"""GOOGLE.CDMCP Tool Interface — Visual browser automation via Chrome CDP.

Provides functions for other tools to inject overlays, manage tab focus,
lock tabs, and highlight elements in Chrome.

Usage from another tool::

    from logic.cdp.overlay import (
        inject_badge, inject_focus, inject_lock,
        inject_highlight, remove_all_overlays,
        get_session, get_session_for_url,
    )
"""

from logic.cdp.overlay import (  # noqa: F401
    inject_badge,
    remove_badge,
    inject_focus,
    remove_focus,
    inject_lock,
    remove_lock,
    is_locked,
    inject_highlight,
    remove_highlight,
    inject_all_overlays,
    remove_all_overlays,
    get_session,
    get_session_for_url,
)
