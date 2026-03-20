"""Cursor IDE-specific system prompts for USERINPUT.

These prompts are injected only when Cursor IDE is detected. They enforce
Cursor-specific constraints (no subagents, etc.).
"""
from typing import List


IDE_CURSOR_PROMPTS: List[str] = [
    "NEVER use the Task tool to launch subagents.",
    (
        "Subagent alternatives: For batch file operations, write a tmp/ Python script. "
        "For parallel exploration, use multiple direct tool calls in a single message. "
        "For complex multi-step tasks, break into sequential inline steps. "
        "This project provides its own orchestration — "
        "Cursor subagents cost 2x credits and lose context."
    ),
]
