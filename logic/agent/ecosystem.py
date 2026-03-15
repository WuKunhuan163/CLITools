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


def _detect_active_layers(root: Path) -> List[str]:
    """Detect which guideline layers are active based on project structure."""
    layers = []
    if (root / "tool" / "OPENCLAW").is_dir():
        layers.append("openclaw")
    return layers


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

    # -- Project summary (compact) --
    project_summary = (
        f"AITerminalTools: {tool_count}+ terminal tools for AI agents. "
        "Tool name = command (GIT, PYTHON, SEARCH). "
        "Architecture: tool/<NAME>/{{main.py, logic/, interface/}}. "
        "Shared: logic/ (internal), interface/ (facade). "
        "Docs: README.md (usage), for_agent.md (internals)."
    )

    # -- Exploration guide (compact) --
    exploration = (
        "Search anything: exec 'TOOL --search all \"query\"'. "
        "Search tools: exec 'TOOL --search tools \"keyword\"'. "
        "Load skill: exec 'SKILLS show <name>'. "
        "Read docs: read_file('tool/<NAME>/for_agent.md'). "
        f"Installed: {', '.join(top_tools[:8])}"
        + (f" +{tool_count - 8} more" if tool_count > 8 else "")
        + "."
    )

    # -- Rationale (compact mental models) --
    rationale = {
        "tools": "Tool = integrated workflow (tool/<NAME>/{main.py, logic/, interface/}). Name IS the command. Fix bugs directly, don't work around them.",
        "docs": "README.md=usage, for_agent.md=architecture, SKILL.md=best practice. Import from interface.*, never logic.* directly.",
        "memory": "Persistent lessons in runtime/experience/. Search: exec 'TOOL --search lessons \"keywords\"'. Record: experience(lesson=..., tool=...).",
        "evolution": "Errors -> Lessons -> Skills -> Infrastructure -> Better Tools. Each fix makes the ecosystem permanently smarter.",
    }

    # -- Standard tools (compact: name=description) --
    has_vision = _has_capability(provider_capabilities, "supports_vision")
    standard_tools = "exec (shell commands; tools=commands), read_file, write_file, edit_file, search, todo, ask_user, experience (record lesson to runtime/experience/)"
    if has_vision:
        standard_tools += ", read_image (vision)"

    # -- Skills (now provided via skill_catalog; just keep the command) --
    skills_usage = "Load any skill: exec 'SKILLS show <name>'. Search: exec 'TOOL --search skills \"topic\"'."

    # -- Expected agent behaviors (compact) --
    agent_behaviors = [
        "BEFORE any task: exec 'TOOL --search all \"task keywords\"' to find tools/lessons/skills. Never code blindly.",
        "Search before creating: no duplicate tools, skills, or lessons. Improve existing ones.",
        "Act immediately. Interleave actions with 1-line status: 'Reading config... Found 3 endpoints. Testing...'",
        "If a tool errors: read source, fix bug directly, retry. Record: experience(lesson=..., tool=...).",
        "Promote knowledge: 3+ lessons on same theme -> create skill. Accumulated skills -> infrastructure.",
        "After changes: update tool's README.md + for_agent.md. Document new infrastructure.",
        "Complete ALL tasks before stopping. User must confirm satisfaction.",
        "Prefer tool calls over reading files. exec 'TOOL --search all X' finds anything.",
        "You may be interrupted at any round. Proactively record key findings via experience() so progress is never lost.",
    ]

    # -- Guidelines (layered: base + optional OPENCLAW) --
    guidelines_text = ""
    try:
        from logic.agent.guidelines import compose_guidelines
        from logic.agent.guidelines.engine import format_guidelines
        active_layers = _detect_active_layers(root)
        gl = compose_guidelines(layers=active_layers, project_root=project_root)
        guidelines_text = format_guidelines(gl)
    except Exception:
        pass

    # -- User-defined rationale (empty by default; OpenClaw will populate) --
    user_rationale = ""

    # -- Skill catalog (Level 1: names + descriptions only) --
    skill_catalog = []
    recent_lessons = []
    try:
        from logic.search.knowledge import KnowledgeManager
        km = KnowledgeManager(root)
        for s in km.get_skill_summary(top_k=20):
            entry = s["name"]
            if s.get("description"):
                entry += f" — {s['description'][:80]}"
            if s.get("tool"):
                entry += f" (tool: {s['tool']})"
            skill_catalog.append(entry)
        for le in km.get_lessons(last_n=5):
            tool_tag = f"[{le['tool']}] " if le.get("tool") else ""
            recent_lessons.append(f"{tool_tag}{le['lesson'][:100]}")
    except Exception:
        pass

    return {
        "project_summary": project_summary,
        "exploration": exploration,
        "rationale": rationale,
        "standard_tools": standard_tools,
        "skills_usage": skills_usage,
        "skill_catalog": skill_catalog,
        "recent_lessons": recent_lessons,
        "agent_behaviors": agent_behaviors,
        "guidelines": guidelines_text,
        "user_rationale": user_rationale,
    }


def build_contextual_suggestions(
    project_root: str,
    user_prompt: str,
    top_k: int = 3,
) -> Dict[str, Any]:
    """Generate per-turn contextual suggestions based on the user's prompt.

    Performs a lightweight semantic search to surface the most relevant
    tools, skills, and lessons for the current task. This gives the agent
    an immediate head start without manual discovery.

    Returns a compact dict suitable for injection into the system feed.
    """
    suggestions: Dict[str, Any] = {}
    if not user_prompt or len(user_prompt.strip()) < 3:
        return suggestions

    try:
        from logic.search.knowledge import KnowledgeManager
        km = KnowledgeManager(project_root)
        results = km.search(user_prompt, scope="all", top_k=top_k * 2)

        tools_found = []
        skills_found = []
        lessons_found = []

        for r in results:
            meta = r.get("meta", {})
            rtype = meta.get("type", "")
            if rtype == "tool" and len(tools_found) < top_k:
                tools_found.append(f"{r['id']} — {meta.get('description', '')[:60]}")
            elif rtype == "skill" and len(skills_found) < top_k:
                skills_found.append(r["id"])
            elif rtype == "lesson" and len(lessons_found) < 2:
                lessons_found.append(meta.get("lesson", "")[:80])

        if tools_found:
            suggestions["relevant_tools"] = tools_found
        if skills_found:
            suggestions["relevant_skills"] = skills_found
        if lessons_found:
            suggestions["relevant_lessons"] = lessons_found
    except Exception:
        pass

    return suggestions


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

    exploration = ecosystem.get("exploration", "")
    if isinstance(exploration, dict):
        for key, val in exploration.items():
            parts.append(f"[{key}] {val}")
    elif exploration:
        parts.append(f"[Explore] {exploration}")

    rationale = ecosystem.get("rationale", {})
    if isinstance(rationale, dict):
        for key, val in rationale.items():
            parts.append(f"[{key}] {val}")

    tools = ecosystem.get("standard_tools", [])
    if isinstance(tools, list) and tools:
        tool_lines = [f"  {t['name']}: {t['desc']}" for t in tools]
        parts.append("[Tools] " + " | ".join(f"{t['name']}" for t in tools))

    if ecosystem.get("skills_usage"):
        parts.append(f"[Skills] {ecosystem['skills_usage']}")

    catalog = ecosystem.get("skill_catalog", [])
    if catalog:
        parts.append("[Skill catalog] " + "; ".join(catalog[:10]))

    lessons = ecosystem.get("recent_lessons", [])
    if lessons:
        parts.append("[Recent lessons] " + " | ".join(lessons[:3]))

    behaviors = ecosystem.get("agent_behaviors", [])
    if isinstance(behaviors, list):
        parts.append("[Behaviors] " + " ".join(f"({i+1}) {b}" for i, b in enumerate(behaviors)))
    elif isinstance(behaviors, dict):
        beh_lines = [f"  - {k}: {v}" for k, v in behaviors.items()]
        parts.append("[Behaviors]\n" + "\n".join(beh_lines))

    if ecosystem.get("guidelines"):
        parts.append(f"[Guidelines]\n{ecosystem['guidelines']}")

    if ecosystem.get("user_rationale"):
        parts.append(f"[User] {ecosystem['user_rationale']}")

    return "\n\n".join(parts) if parts else ""
