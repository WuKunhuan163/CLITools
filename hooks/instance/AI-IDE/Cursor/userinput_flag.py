#!/usr/bin/env python3
"""afterShellExecution hook (matcher: USERINPUT): Flag that USERINPUT was called.

Fires after any shell command containing "USERINPUT". Creates a flag file
so the stop hook knows USERINPUT was executed in this conversation.
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
            f.write(f"[{datetime.now().isoformat()}] userinput_flag: {msg}\n")
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

    conversation_id = payload.get("conversation_id", "unknown")
    command = payload.get("command", "")
    _log(f"command={command[:80]} conv={conversation_id[:12]}")

    if "USERINPUT" in command:
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        flag_file.write_text(command[:200])
        _log(f"FLAG SET at {flag_file}")

    print(json.dumps({}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
