#!/usr/bin/env python3
"""afterShellExecution hook (matcher: USERINPUT): Flag that USERINPUT was called.

Fires after any shell command containing "USERINPUT". Creates a flag file
so the stop hook knows USERINPUT was executed in this conversation.
"""
import json
import sys
from pathlib import Path


def main():
    payload = json.load(sys.stdin)
    conversation_id = payload.get("conversation_id", "unknown")
    command = payload.get("command", "")

    if "USERINPUT" in command:
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        flag_file.write_text(command[:200])

    print(json.dumps({}))


if __name__ == "__main__":
    main()
