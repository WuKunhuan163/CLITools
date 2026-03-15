"""Hook interface: on_tool_exit

Fired when a tool's main execution completes (success or failure).

kwargs:
    tool: ToolBase instance
    exit_code: int (0 = success)
    error: Exception or None
"""
from logic.hooks.engine import HookInterface


class OnToolExit(HookInterface):
    event_name = "on_tool_exit"
    description = "Fired when the tool finishes execution."
