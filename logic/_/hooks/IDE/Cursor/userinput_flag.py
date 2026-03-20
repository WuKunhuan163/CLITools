#!/usr/bin/env python3
"""afterShellExecution hook (matcher: USERINPUT): Flag that USERINPUT completed.

Fires after any shell command containing "USERINPUT". Only sets the success
flag when USERINPUT exits with code 0 (user submitted input). Detects kill
commands and pipe violations that undermine the feedback loop.
"""
import json
import re
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


PIPE_FILTERS = ["| tail", "| head", "| grep", "| awk", "| sed", "| cut", "| sort",
                "|tail", "|head", "|grep", "|awk", "|sed", "|cut", "|sort"]

KILL_PATTERNS = [r"\bkill\b", r"\bpkill\b", r"\bkillall\b", r"kill -[0-9]+",
                 r"kill -TERM", r"kill -KILL", r"kill -INT", r"kill -9"]


def _has_pipe_filter(cmd: str) -> bool:
    lower = cmd.lower()
    return any(f in lower for f in PIPE_FILTERS)


def _is_kill_command(cmd: str) -> bool:
    """Detect commands that kill USERINPUT processes."""
    lower = cmd.lower()
    if "userinput" not in lower:
        return False
    return any(re.search(pat, lower) for pat in KILL_PATTERNS)


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
    exit_code = payload.get("exit_code")
    _log(f"command={command[:80]} exit={exit_code} conv={conversation_id[:12]}")

    output = {}

    if "USERINPUT" not in command:
        print(json.dumps(output))
        return

    if _is_kill_command(command):
        _log(f"VIOLATION: Agent tried to KILL USERINPUT: {command[:120]}")
        flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
        if flag_file.exists():
            flag_file.unlink()
            _log("Cleared flag — USERINPUT was killed, not completed")
        output["message"] = (
            "CRITICAL VIOLATION: You killed USERINPUT. USERINPUT is NOT replaceable "
            "by Cursor Chat. It performs git auto-save, history maintenance, and "
            "ecosystem feedback collection. NEVER kill, cancel, or skip USERINPUT. "
            "Re-run it NOW: python3 tool/USERINPUT/main.py --hint \"...\" "
            "with block_until_ms: 310000"
        )
        print(json.dumps(output))
        return

    if _has_pipe_filter(command):
        _log(f"VIOLATION: USERINPUT output piped through filter: {command[:120]}")
        output["message"] = (
            "CRITICAL VIOLATION: You piped USERINPUT output through a filter "
            "(tail/head/grep/awk/sed). This silently discards the user's response. "
            "NEVER filter USERINPUT output. Re-run USERINPUT without any pipe: "
            "python3 tool/USERINPUT/main.py --hint \"...\" 2>&1"
        )
        print(json.dumps(output))
        return

    if exit_code is not None and exit_code != 0:
        _log(f"USERINPUT exited with code {exit_code} — NOT setting flag")
        output["message"] = (
            f"USERINPUT exited with code {exit_code} (not successful). "
            "This means the user did not submit feedback. Retry: "
            "sleep 30 then re-run USERINPUT --hint \"...\" with block_until_ms: 310000"
        )
        print(json.dumps(output))
        return

    flag_file = Path(f"/tmp/cursor-userinput-done-{conversation_id}")
    flag_file.write_text(command[:200])
    _log(f"FLAG SET at {flag_file} (exit_code={exit_code})")

    print(json.dumps(output))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        _log(f"UNCAUGHT: {traceback.format_exc()}")
        print(json.dumps({}))
