"""Hook interface: on_pre_tool_use

Fired before the agent executes a tool call.

kwargs:
    session_id: str — session identifier
    tool_name: str — name of tool being called (e.g. 'exec', 'read_file')
    tool_args: dict — arguments passed to the tool
    round_num: int — current round number
"""
from interface.hooks import HookInterface


class OnPreToolUse(HookInterface):
    event_name = "on_pre_tool_use"
    description = "Fired before a tool call is executed in the agent loop."
