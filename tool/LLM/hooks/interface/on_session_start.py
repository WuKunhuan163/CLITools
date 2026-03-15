"""Hook interface: on_session_start

Fired when a new agent session begins (ConversationManager.new_session).

kwargs:
    session_id: str — unique session identifier
    codebase_root: str or None — working directory
    title: str — session title
"""
from interface.hooks import HookInterface


class OnSessionStart(HookInterface):
    event_name = "on_session_start"
    description = "Fired when a new agent session is created."
