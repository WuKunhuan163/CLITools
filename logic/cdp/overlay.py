"""Backward-compatibility shim — redirects to tool/GOOGLE.CDMCP/logic/cdp/overlay.py.

All overlay functionality has been moved into the GOOGLE.CDMCP tool.
Use logic.cdmcp_loader.load_cdmcp_overlay() for new code.
"""
from logic.cdmcp_loader import load_cdmcp_overlay as _load

_mod = _load()

# Re-export all public names
get_session = _mod.get_session
get_session_for_url = _mod.get_session_for_url
inject_badge = _mod.inject_badge
remove_badge = _mod.remove_badge
inject_focus = _mod.inject_focus
remove_focus = _mod.remove_focus
inject_lock = _mod.inject_lock
remove_lock = _mod.remove_lock
is_locked = _mod.is_locked
inject_highlight = _mod.inject_highlight
remove_highlight = _mod.remove_highlight
inject_all_overlays = _mod.inject_all_overlays
remove_all_overlays = _mod.remove_all_overlays
inject_favicon = _mod.inject_favicon
activate_tab = _mod.activate_tab
set_lock_passthrough = _mod.set_lock_passthrough
pin_tab = _mod.pin_tab
pin_tab_by_target_id = _mod.pin_tab_by_target_id
get_chrome_tab_id = _mod.get_chrome_tab_id

CDMCP_OVERLAY_ID = _mod.CDMCP_OVERLAY_ID
CDMCP_LOCK_ID = _mod.CDMCP_LOCK_ID
CDMCP_BADGE_ID = _mod.CDMCP_BADGE_ID
CDMCP_FOCUS_ID = _mod.CDMCP_FOCUS_ID
CDMCP_HIGHLIGHT_ID = _mod.CDMCP_HIGHLIGHT_ID
