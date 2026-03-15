#!/usr/bin/env python3
"""sessionStart hook: Inject brain + ecosystem context into Cursor agent.

Fires once when a new Cursor conversation begins. Injects:
1. Brain state (tasks.json, context.md) from runtime/brain/
2. Ecosystem context (skill catalog, exploration guide, agent behaviors)
3. Recent experience lessons from runtime/experience/lessons.jsonl

This gives the Cursor agent the same context-awareness as the LLM tool's agent.
"""
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] brain_inject: {msg}\n")
    except Exception:
        pass


def _load_brain(project_dir: Path) -> list:
    parts = []
    brain_dir = project_dir / "runtime" / "brain"

    tasks_file = brain_dir / "tasks.json"
    if tasks_file.exists():
        try:
            data = json.loads(tasks_file.read_text())
            active = [t for t in data.get("tasks", []) if t.get("status") != "done"]
            if active:
                lines = [f"  #{t['id']} [{t['status']}] {t['content']}" for t in active[:15]]
                parts.append("## Active Tasks\n" + "\n".join(lines))
        except Exception:
            pass

    context_file = brain_dir / "context.md"
    if context_file.exists():
        content = context_file.read_text().strip()
        if content and "not yet initialized" not in content:
            parts.append(f"## Context\n{content}")

    return parts


def _load_lessons(project_dir: Path, count: int = 5) -> list:
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
    except Exception as e:
        _log(f"ecosystem load error: {e}")
    finally:
        if str(project_dir) in sys.path:
            sys.path.remove(str(project_dir))

    return parts


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(f"ERROR parsing stdin: {e}")
        print(json.dumps({}))
        return

    workspace_roots = payload.get("workspace_roots", [])
    project_dir = Path(workspace_roots[0]) if workspace_roots else Path("/Applications/AITerminalTools")
    _log(f"project_dir={project_dir}")

    parts = []
    parts.extend(_load_brain(project_dir))
    parts.extend(_load_lessons(project_dir))
    parts.extend(_load_ecosystem(project_dir))

    cursor_userinput_rule = (
        "\n\n## CRITICAL: USERINPUT\n"
        "You MUST call `USERINPUT` before ending your turn. No exceptions.\n"
        "Cursor may auto-disconnect during USERINPUT's long wait. "
        "If you see 'Launching input GUI...' or waiting messages, the user is still writing. "
        "Keep `sleep`-ing. If all attempts fail, `sleep 30` then `cat <fallback_path>`."
    )

    output = {}
    if parts:
        output["additional_context"] = (
            "--- AGENT BRAIN + ECOSYSTEM ---\n"
            + "\n\n".join(parts)
            + "\n--- END ---\n"
            "Read tasks above and continue where you left off. "
            "Update brain: `python3 bin/BRAIN add/done/list` to manage tasks."
            + cursor_userinput_rule
        )
    else:
        output["additional_context"] = (
            "Agent brain is empty. When the user gives you tasks, "
            "run `python3 bin/BRAIN add \"<task>\"` immediately to record them."
            + cursor_userinput_rule
        )

    result = json.dumps(output)
    _log(f"injected {len(result)} chars, {len(parts)} sections")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
