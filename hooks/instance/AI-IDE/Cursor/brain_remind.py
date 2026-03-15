#!/usr/bin/env python3
"""postToolUse hook: Periodically remind agent to check brain and plan USERINPUT.

Fires after every successful tool call. Uses a counter file to track tool calls
per conversation. Every REMIND_EVERY calls, injects a reminder as
additional_context. Every FULL_INJECT_EVERY calls, injects full brain content.
"""
import json
import sys
import traceback
from pathlib import Path
from datetime import datetime

REMIND_EVERY = 5
FULL_INJECT_EVERY = 20
LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] brain_remind: {msg}\n")
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        _log(f"stdin length={len(raw)}")
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(f"ERROR parsing stdin: {e}")
        print(json.dumps({}))
        return

    conversation_id = payload.get("conversation_id", "unknown")
    tool_name = payload.get("tool_name", "?")
    _log(f"tool={tool_name} conv={conversation_id[:12]}")

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
        project_dir = Path(workspace_roots[0]) if workspace_roots else Path("/Applications/AITerminalTools")
        tasks_file = project_dir / "runtime" / "brain" / "tasks.json"
        tasks_content = ""
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text())
                active = [t for t in data.get("tasks", []) if t.get("status") != "done"]
                if active:
                    tasks_content = "\n".join(
                        f"  #{t['id']} [{t['status']}] {t['content']}"
                        for t in active[:10]
                    )
            except Exception:
                pass

        reminder = f"[BRAIN CHECKPOINT #{count}] "
        if tasks_content:
            reminder += f"Active tasks:\n{tasks_content}\n\n"
        reminder += (
            "ACTION REQUIRED: You MUST call USERINPUT before ending your turn. "
            "Say '[Hook: brain checkpoint received]' NOW to confirm you see this."
        )
        output["additional_context"] = reminder
        _log(f"FULL inject at count={count}")

    elif count % REMIND_EVERY == 0:
        output["additional_context"] = (
            f"[USERINPUT Reminder #{count}] "
            "You MUST call USERINPUT before ending your turn. "
            "Output '[Hook: USERINPUT reminder received]' in your response NOW."
        )
        output["followup_message"] = (
            f"[Hook #{count}] STOP. Output the text "
            "'[Hook: USERINPUT reminder received]' in your response right now, "
            "then continue your work. You MUST call USERINPUT before ending this turn."
        )
        _log(f"REMIND inject at count={count}")
    else:
        _log(f"skip count={count}")

    result = json.dumps(output)
    _log(f"output={result[:200]}")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
