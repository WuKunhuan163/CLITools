"""Hook interface: on_session_end

Fired when an agent session ends (loop completes or is cancelled).

kwargs:
    session_id: str — unique session identifier
    status: str — 'completed', 'cancelled', or 'error'
    round_count: int — total rounds executed
    tool_call_count: int — total tool calls made
"""
from interface.hooks import HookInterface


class OnSessionEnd(HookInterface):
    event_name = "on_session_end"
    description = "Fired when an agent session ends."
