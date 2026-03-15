"""Build ecosystem context for agent prompts.

Constructs a structured context payload that gives a context-free agent
enough information to operate effectively in the AITerminalTools ecosystem
on its very first turn — without needing to read for_agent.md first.

The payload has these sections:
  - project_summary: What AITerminalTools is and its core philosophy
  - exploration: How to discover tools, skills, and documentation
  - rationale: Key mental models the agent needs
  - standard_tools: Tools available to the agent right now
  - skills: Key skills the agent should know about
  - agent_behaviors: Expected behavior patterns
  - user_rationale: User-defined context (empty by default; populated by OpenClaw)
  - system_state: Runtime state injected per-turn (nudges, tool results, etc.)
"""
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def _list_installed_tools(root: Path) -> List[str]:
    """Return names of installed tools (those with main.py)."""
    tool_dir = root / "tool"
    if not tool_dir.is_dir():
        return []
    tools = []
    try:
        for d in sorted(tool_dir.iterdir()):
            if d.is_dir() and (d / "main.py").exists():
                tools.append(d.name)
    except OSError:
        pass
    return tools


def _has_capability(capabilities, attr: str) -> bool:
    """Check if a provider capabilities object has a boolean attribute."""
    return bool(getattr(capabilities, attr, False))


def build_ecosystem_info(
    project_root: str,
    provider_capabilities: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build comprehensive ecosystem context for a context-free agent.

    Args:
        project_root: Absolute path to project root.
        provider_capabilities: Optional provider capabilities object
            to determine which standard tools are available (e.g. vision).

    Returns:
        Dict with structured ecosystem information.
    """
    root = Path(project_root)
    installed_tools = _list_installed_tools(root)
    tool_count = len(installed_tools)
    top_tools = installed_tools[:20]

    # -- Project summary --
    project_summary = (
        "AITerminalTools is a modular terminal tool framework for AI agents and developers. "
        "It provides standardized lifecycle management, GUI integration, multi-language "
        "localization, and isolated Python runtimes for 40+ tools. "
        "Core philosophy: Symmetrical Design — shared logic in root logic/, stable facade "
        "in interface/, each tool in tool/<NAME>/ with its own logic/ and interface/. "
        "In the terminal, every tool name IS a command (e.g. GIT, PYTHON, BILIBILI). "
        "The ecosystem is designed so AI agents can autonomously discover, use, and fix tools."
    )

    # -- Exploration guide --
    exploration = {
        "tool_discovery": (
            "exec(command='TOOL --search tools \"keyword\"') — semantic search across all tools. "
            "exec(command='TOOL --search interfaces \"capability\"') — find cross-tool APIs. "
            "exec(command='TOOL status') — show all installed tools and their health."
        ),
        "skill_discovery": (
            "exec(command='SKILLS search \"topic\"') — semantic search skills. "
            "exec(command='SKILLS show <name>') — read a specific skill guide. "
            "exec(command='SKILLS list') — list all available skills."
        ),
        "documentation_pattern": (
            "Every tool has two key docs: "
            "README.md (usage, commands, examples) and for_agent.md (architecture, internals). "
            "Read them via: read_file(path='tool/<NAME>/README.md') or "
            "read_file(path='tool/<NAME>/for_agent.md'). "
            "The project root for_agent.md is the master reference for the entire framework."
        ),
        "installed_tools": (
            f"{tool_count} tools installed. "
            f"Examples: {', '.join(top_tools[:10])}."
            + (f" ... and {tool_count - 10} more." if tool_count > 10 else "")
        ),
    }

    # -- Rationale (mental models) --
    rationale = {
        "tool_is_command": (
            "In the terminal, tool name = command. 'GIT push' calls the GIT tool. "
            "'BILIBILI --mcp-search query' calls the BILIBILI tool."
        ),
        "what_is_a_tool": (
            "A 'tool' is an integrated automated workflow: a Python package under "
            "tool/<NAME>/ with main.py entry point, logic/ for implementation, "
            "interface/main.py for cross-tool API, hooks/ for event callbacks, "
            "test/ for unit tests. Tools are installable via 'TOOL install <NAME>'."
        ),
        "documentation_hierarchy": (
            "README.md = user-facing usage docs. "
            "for_agent.md = AI-agent-facing architecture guide. "
            "SKILL.md = structured best-practice guide for specific patterns. "
            "Every non-trivial capability should be discoverable from for_agent.md."
        ),
        "import_convention": (
            "Tools import shared utilities from interface.* (stable facade), "
            "never from logic.* directly. Cross-tool imports go through "
            "tool/<NAME>/interface/main.py."
        ),
        "tools_may_be_buggy": (
            "Tools may have bugs. When a tool errors, read its source code, "
            "fix the bug directly, then retry. Record the fix as a lesson "
            "via 'SKILLS learn \"description\" --tool NAME'."
        ),
        "evolution_cycle": (
            "Errors -> Lessons (runtime/experience/lessons.jsonl) -> "
            "Skills (skills/core/) -> Infrastructure (interface.*) -> "
            "Better code. Each fix makes the ecosystem smarter."
        ),
    }

    # -- Standard tools available to the agent --
    has_vision = _has_capability(provider_capabilities, "supports_vision")
    standard_tools = [
        {"name": "exec", "desc": "Run shell commands. Tools are commands (e.g. exec 'GIT status'). Timeout auto-backgrounds."},
        {"name": "read_file", "desc": "Read file contents. Use to inspect code, docs, configs."},
        {"name": "write_file", "desc": "Create or overwrite a file. Content must be the complete file."},
        {"name": "edit_file", "desc": "Replace specific text in a file. First read_file, then precise replacement."},
        {"name": "search", "desc": "Search for text/code patterns across the project."},
        {"name": "todo", "desc": "Manage task lists: create, update, delete items."},
        {"name": "ask_user", "desc": "Ask the user a question. User will respond in a follow-up message."},
    ]
    if has_vision:
        standard_tools.append(
            {"name": "read_image", "desc": "Read and analyze image files (requires vision model)."}
        )

    # -- Skills hints --
    skills = {
        "key_skills": [
            "tool-development-workflow — creating and deploying tools",
            "code-quality-review — static analysis and quality auditing",
            "error-recovery-patterns — retry, fallback, partial failure handling",
            "exploratory-testing — investigating unknown APIs via tmp/ scripts",
            "turing-machine-development — progress display system",
            "openclaw — self-improvement loop: lesson -> skill -> infrastructure",
        ],
        "how_to_use": "exec(command='SKILLS show <name>') to load any skill.",
    }

    # -- Expected agent behaviors --
    agent_behaviors = {
        "act_first": "Use tools immediately. Don't just describe changes — apply them.",
        "explore_then_fix": "When stuck, search for existing tools/skills/code before writing new.",
        "fix_bugs": "If a tool errors, read its source, fix the bug, then retry.",
        "complete_all_tasks": "Ensure ALL requested tasks are done before stopping.",
        "verify_work": "After writing files, optionally read_file to verify. Run tests if applicable.",
        "use_userinput": "After completing tasks, the orchestrator will collect user feedback.",
        "record_lessons": "After non-trivial fixes, record lessons via SKILLS learn.",
        "encapsulate_patterns": "Repeated patterns should become skills or infrastructure.",
    }

    # -- User-defined rationale (empty by default; OpenClaw will populate) --
    user_rationale = ""

    return {
        "project_summary": project_summary,
        "exploration": exploration,
        "rationale": rationale,
        "standard_tools": standard_tools,
        "skills": skills,
        "agent_behaviors": agent_behaviors,
        "user_rationale": user_rationale,
    }


def build_system_state(
    session_env: Optional[Any] = None,
    nudge_triggered: bool = False,
    quality_warnings: Optional[Dict[str, List[str]]] = None,
    last_tool_results: Optional[List[Dict]] = None,
) -> Dict[str, Any]:
    """Build per-turn system state for the agent feed.

    This is injected alongside the user event each turn, giving the agent
    awareness of what happened since the last turn.

    Args:
        session_env: AgentEnvironment with discovered tools/skills/results.
        nudge_triggered: Whether a nudge was triggered this turn.
        quality_warnings: Any unfixed quality warnings from previous writes.
        last_tool_results: Recent tool call results for awareness.

    Returns:
        Dict with system state.
    """
    state: Dict[str, Any] = {
        "nudge_triggered": nudge_triggered,
    }

    if quality_warnings:
        state["quality_warnings"] = {
            k: v for k, v in list(quality_warnings.items())[:3]
        }

    if last_tool_results:
        state["recent_results"] = last_tool_results[-5:]

    if session_env:
        try:
            if hasattr(session_env, "visible_tools") and session_env.visible_tools:
                state["discovered_tools"] = list(session_env.visible_tools.keys())
            if hasattr(session_env, "errors") and session_env.errors:
                state["active_errors"] = session_env.errors[-3:]
            if hasattr(session_env, "lessons") and session_env.lessons:
                state["lessons_this_session"] = session_env.lessons[-3:]
        except Exception:
            pass

    return state


def format_ecosystem_for_prompt(ecosystem: Dict[str, Any]) -> str:
    """Format ecosystem dict as a compact string for the LLM context window.

    Used when injecting ecosystem info directly into the message text
    (as opposed to structured JSON in the event payload).
    """
    parts = []

    if ecosystem.get("project_summary"):
        parts.append(f"[Project] {ecosystem['project_summary']}")

    exploration = ecosystem.get("exploration", {})
    if isinstance(exploration, dict):
        for key, val in exploration.items():
            parts.append(f"[{key}] {val}")
    elif exploration:
        parts.append(f"[Exploration] {exploration}")

    rationale = ecosystem.get("rationale", {})
    if isinstance(rationale, dict):
        for key, val in rationale.items():
            parts.append(f"[{key}] {val}")

    tools = ecosystem.get("standard_tools", [])
    if isinstance(tools, list) and tools:
        tool_lines = [f"  - {t['name']}: {t['desc']}" for t in tools]
        parts.append("[Standard tools]\n" + "\n".join(tool_lines))

    skills = ecosystem.get("skills", {})
    if isinstance(skills, dict) and skills.get("key_skills"):
        parts.append("[Key skills] " + "; ".join(skills["key_skills"]))
        if skills.get("how_to_use"):
            parts.append(f"[Skills usage] {skills['how_to_use']}")

    behaviors = ecosystem.get("agent_behaviors", {})
    if isinstance(behaviors, dict):
        beh_lines = [f"  - {k}: {v}" for k, v in behaviors.items()]
        parts.append("[Expected behaviors]\n" + "\n".join(beh_lines))

    if ecosystem.get("user_rationale"):
        parts.append(f"[User rationale] {ecosystem['user_rationale']}")

    return "\n\n".join(parts) if parts else ""
