#!/usr/bin/env python3
"""
USERINPUT Tool Interface

Provides functions for other tools to collect user feedback via GUI
without the full USERINPUT overhead (no auto-commit, no system prompts).
"""

def get_user_feedback(hint="", timeout=300, title="Feedback"):
    """
    Launch a USERINPUT GUI window and return the user's text input.
    
    Unlike the full USERINPUT command, this:
    - Does NOT auto-commit
    - Does NOT append system prompts
    - Returns only the raw user text (str), or None on timeout/cancel/error
    """
    from tool.USERINPUT.main import get_user_input_tkinter
    try:
        result = get_user_input_tkinter(
            title=title, timeout=timeout, hint_text=hint
        )
        if result is None:
            return None
        if result.startswith("__PARTIAL_TIMEOUT__:"):
            return result[len("__PARTIAL_TIMEOUT__:"):]
        return result
    except Exception:
        return None


def get_user_feedback_func():
    """Factory: returns the get_user_feedback function for deferred use."""
    return get_user_feedback
