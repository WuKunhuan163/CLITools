"""Hook interface: on_user_submit

Fired after the user submits their input (clicks Submit or presses Enter).

kwargs:
    tool: ToolBase instance
    user_text: str
    elapsed_sec: float (time from GUI show to submit)
"""
from logic.hooks.engine import HookInterface


class OnUserSubmit(HookInterface):
    event_name = "on_user_submit"
    description = "Fired when the user submits their input."
