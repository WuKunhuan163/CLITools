"""Hook event: before_tool_call

Fires before a tool's main logic executes. Used for:
- Skills matching via semantic search
- Pre-flight validation
- Audit logging

Kwargs:
    tool: ToolBase instance
    command: str - the command/args being executed
    description: str - semantic description of what the call does
"""
from logic._.hooks.engine import HookInterface


class BeforeToolCallHook(HookInterface):
    event_name = "before_tool_call"
    description = "Fires before tool execution. Use for skills scan, preflight checks."
