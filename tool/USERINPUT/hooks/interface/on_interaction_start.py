"""Hook interface: on_interaction_start

Fired when USERINPUT begins an interaction cycle — before any GUI or
file-based fallback is shown. This is the earliest point at which the
tool knows it will collect user input.

kwargs:
    tool: ToolBase instance
    hint: str (the --hint text, or "")
    mode: str ("gui" | "fallback" | "remote")
"""
from logic.hooks.engine import HookInterface


class OnInteractionStart(HookInterface):
    event_name = "on_interaction_start"
    description = "Fired when USERINPUT begins collecting user input."
