"""Agent nudge detection — identifies when the agent needs redirection.

Detects patterns like:
- Agent describes changes without applying them
- Agent produces empty responses
- Unresolved quality warnings
- Unverified writes
"""
from typing import Dict, List, Optional


def should_nudge(text: str) -> bool:
    """Detect if the agent described code changes without applying them.

    Returns True if the text looks like a description of changes rather
    than a final answer.
    """
    text_lower = text.lower()
    code_indicators = ["```", "def ", "class ", "import ",
                       "<html", "function ", "const "]
    has_code = any(ind in text_lower for ind in code_indicators)

    action_indicators = ["here's the updated", "here is the", "i would",
                         "you can add", "modify", "change the",
                         "update the", "replace", "add the following",
                         "here's how"]
    has_action_desc = any(ind in text_lower for ind in action_indicators)

    applied_indicators = ["i've created", "i've updated", "i've fixed",
                          "i have created", "i have updated", "done.",
                          "file has been", "successfully"]
    already_applied = any(ind in text_lower for ind in applied_indicators)

    return (has_code or has_action_desc) and not already_applied


def build_nudge_message(has_read: bool = False) -> str:
    """Build a nudge message to redirect the agent to use tools."""
    if has_read:
        return (
            "You already read the file. Now use write_file to apply your fix. "
            "The content parameter must be the COMPLETE file with ALL imports, "
            "functions, and your changes merged in.")
    return (
        "You described changes but didn't apply them. First read_file to get "
        "the current content, then use write_file with the COMPLETE file.")


def build_quality_nudge(warnings: Dict[str, List[str]]) -> Optional[str]:
    """Build a nudge about unresolved quality warnings."""
    if not warnings:
        return None
    parts = []
    for fpath, warns in list(warnings.items())[:2]:
        import os
        fname = os.path.basename(fpath)
        parts.append(f"{fname}: " + "; ".join(warns[:2]))
    return "UNRESOLVED QUALITY ISSUES — fix these before finishing:\n" + "\n".join(parts)


def build_verify_nudge(unverified: List[str]) -> Optional[str]:
    """Build a nudge about unverified writes."""
    if not unverified:
        return None
    import os
    return (
        f"You wrote {len(unverified)} file(s) but never read them back. "
        f"Use read_file to confirm changes: "
        + ", ".join(os.path.basename(p) for p in unverified[:3]))
