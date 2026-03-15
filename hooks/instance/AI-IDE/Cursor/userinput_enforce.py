#!/usr/bin/env python3
"""stop hook: Enforce USERINPUT execution before agent stops.

Fires when the agent loop ends. Checks if USERINPUT was called during this
conversation (via flag file from userinput_flag.py). If not, returns a
followup_message that auto-submits, forcing the agent to continue and call
USERINPUT.

loop_limit in hooks.json caps retries (recommended: 2).
"""
import json
import sys
from pathlib import Path


def main():
    payload = json.load(sys.stdin)
    status = payload.get("status", "completed")
    loop_count = payload.get("loop_count", 0)
    conversation_id = payload.get("conversation_id", "unknown")

    output = {}

    if status == "completed" and loop_count < 2:
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        if not flag_file.exists():
            workspace_roots = payload.get("workspace_roots", [])
            project_dir = Path(workspace_roots[0]) if workspace_roots else Path(".")
            tasks_file = project_dir / "runtime" / "brain" / "tasks.md"
            has_tasks = False
            if tasks_file.exists():
                content = tasks_file.read_text().strip()
                has_tasks = content and "No active tasks" not in content

            msg = (
                "⛔ STOP — You have NOT called USERINPUT yet. "
                "You MUST execute `USERINPUT` as a shell command RIGHT NOW. "
                "Do not do anything else first. Just run: USERINPUT"
            )
            if has_tasks:
                msg += "\nThen update runtime/brain/tasks.md."

            output["followup_message"] = msg

    print(json.dumps(output))


if __name__ == "__main__":
    main()
