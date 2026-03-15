#!/usr/bin/env python3
"""sessionStart hook: Inject brain + ecosystem context into Cursor agent.

Fires once when a new Cursor conversation begins. Injects:
1. Brain state (tasks.md, context.md) from runtime/brain/
2. Ecosystem context (skill catalog, exploration guide, agent behaviors) from logic/agent/ecosystem.py
3. Recent experience lessons from runtime/experience/lessons.jsonl

This gives the Cursor agent the same context-awareness as the LLM tool's agent.
"""
import json
import os
import sys
from pathlib import Path


def _load_brain(project_dir: Path) -> list:
    """Load brain state files."""
    parts = []
    brain_dir = project_dir / "runtime" / "brain"

    for fname, label in [("tasks.md", "Tasks"), ("context.md", "Context")]:
        fpath = brain_dir / fname
        if fpath.exists():
            content = fpath.read_text().strip()
            if content and "No active tasks" not in content and "not yet initialized" not in content:
                parts.append(f"## {label}\n{content}")

    return parts


def _load_lessons(project_dir: Path, count: int = 5) -> list:
    """Load recent experience lessons."""
    parts = []
    experience_file = project_dir / "runtime" / "experience" / "lessons.jsonl"
    if experience_file.exists():
        lines = experience_file.read_text().strip().split("\n")
        recent = lines[-count:] if len(lines) > count else lines
        lessons = []
        for line in recent:
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                lessons.append(f"- [{obj.get('severity', 'info')}] {obj.get('lesson', '')[:120]}")
            except json.JSONDecodeError:
                pass
        if lessons:
            parts.append("## Recent Lessons\n" + "\n".join(lessons))

    return parts


def _load_ecosystem(project_dir: Path) -> list:
    """Load ecosystem context via logic/agent/ecosystem.py."""
    parts = []
    sys.path.insert(0, str(project_dir))
    try:
        from logic.agent.ecosystem import build_ecosystem_info
        eco = build_ecosystem_info(str(project_dir))

        if eco.get("guidelines"):
            parts.append(f"## Guidelines\n{eco['guidelines']}")

        if eco.get("skill_catalog"):
            catalog_str = "\n".join(f"- {s}" for s in eco["skill_catalog"][:15])
            parts.append(f"## Available Skills\n{catalog_str}\nLoad: exec 'SKILLS show <name>'")

        if eco.get("agent_behaviors"):
            behaviors = "\n".join(f"- {b}" for b in eco["agent_behaviors"])
            parts.append(f"## Agent Behaviors\n{behaviors}")

        if eco.get("exploration"):
            parts.append(f"## Exploration\n{eco['exploration']}")

    except Exception:
        pass
    finally:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))

    return parts


def main():
    payload = json.load(sys.stdin)
    workspace_roots = payload.get("workspace_roots", [])
    project_dir = Path(workspace_roots[0]) if workspace_roots else Path(".")

    parts = []
    parts.extend(_load_brain(project_dir))
    parts.extend(_load_lessons(project_dir))
    parts.extend(_load_ecosystem(project_dir))

    output = {}
    if parts:
        output["additional_context"] = (
            "--- AGENT BRAIN + ECOSYSTEM ---\n"
            + "\n\n".join(parts)
            + "\n--- END ---\n"
            "Read tasks above and continue where you left off. "
            "Update runtime/brain/tasks.md and runtime/brain/context.md as you work. "
            "Use 'SKILLS show <name>' to load relevant skills before starting new work."
        )
    else:
        output["additional_context"] = (
            "Agent brain at runtime/brain/ is empty. "
            "When the user gives you tasks, write them to runtime/brain/tasks.md immediately. "
            "Use 'SKILLS show <name>' to discover relevant skills."
        )

    print(json.dumps(output))


if __name__ == "__main__":
    main()
