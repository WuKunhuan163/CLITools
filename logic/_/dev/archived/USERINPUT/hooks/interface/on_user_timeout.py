"""Hook interface: on_user_timeout

Fired when the input times out without user response.

kwargs:
    tool: ToolBase instance
    timeout_sec: int
    partial_text: str (any partial text the user had typed)
"""
from interface.hooks import HookInterface


class OnUserTimeout(HookInterface):
    event_name = "on_user_timeout"
    description = "Fired when the input collection times out."
