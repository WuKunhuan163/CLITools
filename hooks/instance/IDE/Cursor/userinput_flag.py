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


PIPE_FILTERS = ["| tail", "| head", "| grep", "| awk", "| sed", "| cut", "| sort", "|tail", "|head", "|grep", "|awk", "|sed", "|cut", "|sort"]


def _has_pipe_filter(cmd: str) -> bool:
    """Check if a USERINPUT command is piped through a filter."""
    lower = cmd.lower()
    return any(f in lower for f in PIPE_FILTERS)


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

    output = {}

    if "USERINPUT" in command:
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        flag_file.write_text(command[:200])
        _log(f"FLAG SET at {flag_file}")

        if _has_pipe_filter(command):
            _log(f"VIOLATION: USERINPUT output piped through filter: {command[:120]}")
            output["message"] = (
                "CRITICAL VIOLATION: You piped USERINPUT output through a filter "
                "(tail/head/grep/awk/sed). This silently discards the user's response. "
                "NEVER filter USERINPUT output. Re-run USERINPUT without any pipe: "
                "python3 tool/USERINPUT/main.py --hint \"...\" 2>&1"
            )

    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
