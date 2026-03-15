"""Hook interface: on_user_cancel

Fired when the user cancels the input (closes window, clicks Cancel).

kwargs:
    tool: ToolBase instance
    reason: str ("closed" | "cancelled" | "escaped")
"""
from interface.hooks import HookInterface


class OnUserCancel(HookInterface):
    event_name = "on_user_cancel"
    description = "Fired when the user cancels input without submitting."
