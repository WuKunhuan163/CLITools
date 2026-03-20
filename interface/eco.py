"""Ecosystem navigation interface.

Unified CLI for exploring the AITerminalTools ecosystem:
tools, skills, brain, docs, and blueprint-defined commands.

Quick start::

    from interface.eco import eco_dashboard, eco_search, eco_tool

    eco_dashboard(root)           # print ecosystem overview
    eco_search(root, "rate limit")  # unified semantic search
    eco_tool(root, "LLM")        # tool deep-dive
"""
from pathlib import Path
from typing import Optional


def eco_dashboard(root, *, _print=True) -> dict:
    """Show ecosystem overview dashboard."""
    from logic._.eco.navigation import get_dashboard
    return get_dashboard(Path(root))


def eco_search(root, query: str, scope: str = "all", top_k: int = 10, tool: str = None):
    """Unified semantic search across the ecosystem."""
    from interface.search import search_all, search_tools, search_skills, search_lessons, search_docs
    root = Path(root)
    if scope == "all":
        return search_all(root, query, top_k=top_k, tool=tool)
    elif scope == "tools":
        return search_tools(root, query, top_k=top_k)
    elif scope == "skills":
        return search_skills(root, query, top_k=top_k, tool_name=tool)
    elif scope == "lessons":
        return search_lessons(root, query, top_k=top_k, tool=tool)
    elif scope == "docs":
        return search_docs(root, query, top_k=top_k)
    return search_all(root, query, top_k=top_k, tool=tool)


def eco_tool(root, name: str) -> Optional[dict]:
    """Get comprehensive info about a specific tool."""
    from logic._.eco.navigation import get_tool_info
    return get_tool_info(Path(root), name)


def eco_skill(root, name: str) -> Optional[str]:
    """Get skill content by name."""
    from logic._.eco.navigation import get_skill_content
    return get_skill_content(Path(root), name)


def eco_map(root) -> dict:
    """Get ecosystem directory structure map."""
    from logic._.eco.navigation import get_ecosystem_map
    return get_ecosystem_map(Path(root))


def eco_here(root, cwd: str = None) -> dict:
    """Context-aware navigation based on CWD."""
    import os
    from logic._.eco.navigation import get_context_here
    return get_context_here(Path(root), cwd or os.getcwd())


def eco_guide(root) -> str:
    """Get onboarding guide for context-free assistants."""
    from logic._.eco.navigation import get_onboarding_guide
    return get_onboarding_guide(Path(root))


def eco_blueprint_commands(root) -> dict:
    """List blueprint-defined shortcut commands."""
    from logic._.eco.navigation import get_blueprint_commands
    return get_blueprint_commands(Path(root))


def eco_run_command(root, cmd_name: str) -> Optional[str]:
    """Get the shell command for a blueprint-defined shortcut."""
    from logic._.eco.navigation import run_blueprint_command
    return run_blueprint_command(Path(root), cmd_name)


__all__ = [
    "eco_dashboard",
    "eco_search",
    "eco_tool",
    "eco_skill",
    "eco_map",
    "eco_here",
    "eco_guide",
    "eco_blueprint_commands",
    "eco_run_command",
]
