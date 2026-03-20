"""Hook event: after_tool_call

Fires after a tool's main logic completes. Used for:
- Recording experience/lessons
- Updating brain context
- Audit logging

Kwargs:
    tool: ToolBase instance
    command: str - the command/args that were executed
    result: Any - the result/return value (if available)
    success: bool - whether the call succeeded
"""
from logic._.hooks.engine import HookInterface


class AfterToolCallHook(HookInterface):
    event_name = "after_tool_call"
    description = "Fires after tool execution. Use for experience recording, brain updates."
