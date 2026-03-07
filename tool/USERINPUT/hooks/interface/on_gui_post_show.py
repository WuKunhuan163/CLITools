"""Hook interface: on_gui_post_show

Fired after the GUI window has been shown and the main loop has started.

kwargs:
    tool: ToolBase instance
    window_id: str (tkinter window identifier, or "")
"""
from logic.tool.hooks.engine import HookInterface


class OnGuiPostShow(HookInterface):
    event_name = "on_gui_post_show"
    description = "Fired after the GUI window has been displayed."
