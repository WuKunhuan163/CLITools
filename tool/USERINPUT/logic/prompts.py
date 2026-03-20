"""Default system prompts for USERINPUT.

Universal prompts apply to all agents. Project prompts apply when the TOOL
ecosystem is present. IDE-specific prompts are loaded from their respective
setup modules (e.g., logic/_/setup/IDE/cursor/prompts.py).
"""
from typing import List


UNIVERSAL_PROMPTS: List[str] = [
    (
        "CRITICAL: Execute USERINPUT after EVERY task completion, error, or fix "
        "— never end your turn without at least one USERINPUT call. "
        "USERINPUT is NOT Cursor Chat — it performs git auto-save, history maintenance, "
        "and ecosystem feedback. NEVER kill, cancel, or skip it. "
        "If timeout/empty, sleep 30-60s and retry. "
        "Use USERINPUT --enquiry --hint for mid-task questions."
    ),
    (
        "Bold status labels only, minimal coloring. "
        "Grammar: Verb + Noun or Adverb + Verb "
        "(e.g., 'Failed to install', 'Successfully saved'). "
        "Subsequent parts are complements. No emojis."
    ),
    (
        "Frequently refine README.md and AGENT.md. "
        "When creating skills, tools, or tests, always consider "
        "discoverability for context-free agents."
    ),
    (
        "Fix problems yourself first. Debug via tmp/ log files. "
        "Search for existing code before writing new implementations."
    ),
    (
        "When switching to a new task, first search relevant "
        "README.md, AGENT.md, and skill files before implementation."
    ),
]

PROJECT_PROMPTS: List[str] = [
    (
        "Use absolute paths for tool call arguments. "
        "Use 'TOOL --lang audit' and 'TOOL --audit code' for quality checks."
    ),
]


def get_default_prompts(include_ide: bool = True, include_project: bool = True) -> List[str]:
    """Build the default system prompt list based on environment.

    Parameters
    ----------
    include_ide : bool
        Whether to include IDE-specific prompts (auto-detected if True).
    include_project : bool
        Whether to include project-ecosystem prompts.
    """
    prompts = list(UNIVERSAL_PROMPTS)

    if include_project:
        prompts.extend(PROJECT_PROMPTS)

    if include_ide:
        try:
            from logic._.utils.system import is_cursor_ide
            if is_cursor_ide():
                from logic._.setup.IDE.cursor.prompts import IDE_CURSOR_PROMPTS
                prompts.extend(IDE_CURSOR_PROMPTS)
        except ImportError:
            pass

    return prompts
