"""Re-export overlay functions from the shared logic.cdp.overlay module."""
from logic.cdp.overlay import (  # noqa: F401
    CDMCP_OVERLAY_ID, CDMCP_LOCK_ID, CDMCP_BADGE_ID,
    CDMCP_FOCUS_ID, CDMCP_HIGHLIGHT_ID,
    get_session, get_session_for_url,
    inject_badge, remove_badge,
    inject_focus, remove_focus,
    inject_lock, remove_lock, is_locked,
    inject_highlight, remove_highlight,
    inject_all_overlays, remove_all_overlays,
)
