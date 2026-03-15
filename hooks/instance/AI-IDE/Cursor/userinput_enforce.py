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
import traceback
from pathlib import Path
from datetime import datetime

LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] userinput_enforce: {msg}\n")
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception as e:
        _log(f"ERROR parsing stdin: {e}")
        print(json.dumps({}))
        return

    status = payload.get("status", "completed")
    loop_count = payload.get("loop_count", 0)
    conversation_id = payload.get("conversation_id", "unknown")
    _log(f"status={status} loop={loop_count} conv={conversation_id[:12]}")

    output = {}

    if status == "completed" and loop_count < 2:
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        if not flag_file.exists():
            _log("USERINPUT NOT called — injecting followup_message")
            # output["followup_message"] = (
            #     "STOP. You have NOT called USERINPUT yet. "
            #     "Execute `USERINPUT` as a shell command RIGHT NOW. "
            #     "Do not do anything else first."
            # )
        else:
            _log("USERINPUT was called — no action needed")
    else:
        _log(f"skip: status={status}, loop={loop_count}")

    result = json.dumps(output)
    _log(f"output={result[:200]}")
    print(result)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
