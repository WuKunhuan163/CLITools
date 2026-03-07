"""Hook interface: on_gui_pre_show

Fired just before the tkinter GUI window is shown to the user.

kwargs:
    tool: ToolBase instance
    hint: str
    timeout: int (seconds)
    title: str
"""
from logic.hooks.engine import HookInterface


class OnGuiPreShow(HookInterface):
    event_name = "on_gui_pre_show"
    description = "Fired immediately before the GUI window is displayed."
