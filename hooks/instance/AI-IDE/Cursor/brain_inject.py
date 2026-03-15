#!/usr/bin/env python3
"""sessionStart hook: Read runtime/brain/ and inject into conversation context.

Fires once when a new Cursor conversation begins. Reads tasks.md and context.md
from runtime/brain/ and returns them as additional_context so the agent starts
with full awareness of its current work state.
"""
import json
import sys
from pathlib import Path


def main():
    payload = json.load(sys.stdin)
    workspace_roots = payload.get("workspace_roots", [])
    project_dir = Path(workspace_roots[0]) if workspace_roots else Path(".")

    brain_dir = project_dir / "runtime" / "brain"
    parts = []

    for fname, label in [("tasks.md", "Tasks"), ("context.md", "Context")]:
        fpath = brain_dir / fname
        if fpath.exists():
            content = fpath.read_text().strip()
            if content and "No active tasks" not in content and "not yet initialized" not in content:
                parts.append(f"## {label}\n{content}")

    experience_file = project_dir / "runtime" / "experience" / "lessons.jsonl"
    if experience_file.exists():
        lines = experience_file.read_text().strip().split("\n")
        recent = lines[-5:] if len(lines) > 5 else lines
        if recent and recent[0]:
            lessons = []
            for line in recent:
                try:
                    obj = json.loads(line)
                    lessons.append(f"- [{obj.get('severity', 'info')}] {obj.get('lesson', '')[:120]}")
                except json.JSONDecodeError:
                    pass
            if lessons:
                parts.append("## Recent Experience\n" + "\n".join(lessons))

    output = {}
    if parts:
        output["additional_context"] = (
            "--- AGENT BRAIN (runtime/brain/) ---\n"
            + "\n\n".join(parts)
            + "\n--- END BRAIN ---\n"
            "Read these tasks and continue where you left off. "
            "Update runtime/brain/tasks.md and runtime/brain/context.md as you work."
        )
    else:
        output["additional_context"] = (
            "Agent brain at runtime/brain/ is empty. "
            "When the user gives you tasks, write them to runtime/brain/tasks.md immediately."
        )

    print(json.dumps(output))


if __name__ == "__main__":
    main()
