"""Hook interface: on_turn_start

Fired at the start of each agent turn (user sends a message).

kwargs:
    session_id: str — session identifier
    user_text: str — the user's message
    message_count: int — total messages in session so far
"""
from interface.hooks import HookInterface


class OnTurnStart(HookInterface):
    event_name = "on_turn_start"
    description = "Fired when a new agent turn begins (user message received)."
