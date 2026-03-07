"""Hook interface: on_tool_start

Fired when a tool's main() begins execution, after ToolBase.__init__
and handle_command_line have completed without early exit.

kwargs:
    tool: ToolBase instance
    args: parsed argparse.Namespace (or None if no parser)
"""
from logic.hooks.engine import HookInterface


class OnToolStart(HookInterface):
    event_name = "on_tool_start"
    description = "Fired when the tool begins its main execution."
