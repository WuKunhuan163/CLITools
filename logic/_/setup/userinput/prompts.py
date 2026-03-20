"""Default system prompts for USERINPUT setup.

These are mature, validated prompts that apply universally to any agent using
USERINPUT. Called during `USERINPUT setup` to populate config.json.

Prompts are organized into tiers:
  - UNIVERSAL: Apply to all agents in any environment
  - IDE_CURSOR: Cursor IDE-specific (injected only when Cursor is detected)
  - PROJECT: Project-ecosystem-specific (injected when TOOL ecosystem is present)
"""
from typing import List


UNIVERSAL_PROMPTS: List[str] = [
    (
        "CRITICAL: Execute USERINPUT after EVERY task completion, error, or fix "
        "— never end your turn without at least one USERINPUT call. "
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

IDE_CURSOR_PROMPTS: List[str] = [
    "NEVER use the Task tool to launch subagents.",
    (
        "Subagent alternatives: For batch file operations, write a tmp/ Python script. "
        "For parallel exploration, use multiple direct tool calls in a single message. "
        "For complex multi-step tasks, break into sequential inline steps. "
        "This project provides its own orchestration via OPENCLAW — "
        "Cursor subagents cost 2x credits and lose context."
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
            from logic.utils.system import is_cursor_ide
            if is_cursor_ide():
                prompts.extend(IDE_CURSOR_PROMPTS)
        except ImportError:
            pass

    return prompts
