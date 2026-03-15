#!/usr/bin/env python3
"""postToolUse hook: Periodically remind agent to check brain and plan USERINPUT.

Fires after every successful tool call. Uses a counter file to track tool calls
per conversation. Every REMIND_EVERY calls, injects a light reminder as
additional_context. Every FULL_INJECT_EVERY calls, injects the full brain content.
"""
import json
import sys
from pathlib import Path

REMIND_EVERY = 5
FULL_INJECT_EVERY = 15


def main():
    payload = json.load(sys.stdin)
    conversation_id = payload.get("conversation_id", "unknown")

    counter_file = Path(f"/tmp/cursor-brain-counter-{conversation_id}")
    count = 0
    if counter_file.exists():
        try:
            count = int(counter_file.read_text().strip())
        except (ValueError, OSError):
            count = 0
    count += 1
    counter_file.write_text(str(count))

    output = {}

    if count % FULL_INJECT_EVERY == 0:
        workspace_roots = payload.get("workspace_roots", [])
        project_dir = Path(workspace_roots[0]) if workspace_roots else Path(".")
        tasks_file = project_dir / "runtime" / "brain" / "tasks.md"
        tasks_content = ""
        if tasks_file.exists():
            tasks_content = tasks_file.read_text().strip()

        reminder = f"[BRAIN CHECKPOINT #{count}] "
        if tasks_content and "No active tasks" not in tasks_content:
            reminder += f"Current tasks:\n{tasks_content}\n\n"
        reminder += (
            "ACTION REQUIRED: "
            "(1) Update runtime/brain/tasks.md with your progress. "
            "(2) Update runtime/brain/context.md with what you're doing. "
            "(3) You MUST call USERINPUT before ending your turn."
        )
        output["additional_context"] = reminder

    elif count % REMIND_EVERY == 0:
        output["additional_context"] = (
            f"[Reminder #{count}] "
            "Check runtime/brain/tasks.md — are you on track? "
            "Remember: USERINPUT before ending your turn."
        )

    print(json.dumps(output))


if __name__ == "__main__":
    main()
