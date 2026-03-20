"""Hook interface: on_post_tool_use

Fired after the agent executes a tool call.

kwargs:
    session_id: str — session identifier
    tool_name: str — name of tool called
    tool_args: dict — arguments that were passed
    result: dict — tool execution result {'ok': bool, 'output': str}
    round_num: int — current round number
    duration_ms: float — execution time in milliseconds
"""
from interface.hooks import HookInterface


class OnPostToolUse(HookInterface):
    event_name = "on_post_tool_use"
    description = "Fired after a tool call completes in the agent loop."
