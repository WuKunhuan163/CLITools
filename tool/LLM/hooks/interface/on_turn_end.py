"""Hook interface: on_turn_end

Fired when an agent turn completes (all rounds for this user message done).

kwargs:
    session_id: str — session identifier
    round_count: int — rounds used in this turn
    tool_calls_count: int — tool calls made in this turn
    status: str — 'completed', 'cancelled', 'turn_limit', or 'error'
"""
from interface.hooks import HookInterface


class OnTurnEnd(HookInterface):
    event_name = "on_turn_end"
    description = "Fired when an agent turn completes."
