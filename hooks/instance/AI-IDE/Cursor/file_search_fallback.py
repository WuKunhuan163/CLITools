#!/usr/bin/env python3
"""postToolUse hook: When Glob/Grep returns empty, remind to use ls/find for
files with spaces or unusual names. Also handles @-referenced paths that may
not include quotes.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

LOG_FILE = Path("/tmp/cursor-hooks.log")


def _log(msg: str):
    try:
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] file_search_fallback: {msg}\n")
    except Exception:
        pass


def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        print(json.dumps({}))
        return

    tool_name = payload.get("tool_name", "")
    tool_output = payload.get("tool_output", "")
    tool_input = json.dumps(payload.get("tool_input", {}))

    _log(f"tool={tool_name}")

    if tool_name in ("Glob", "Grep", "SemanticSearch"):
        if "0 files found" in tool_output or "No matches found" in tool_output:
            hint = (
                "[File Search Fallback] Search returned empty. "
                "User @-references may contain SPACES in filenames (e.g. 'Screenshot 2026-03-13 at 19.03.44.png'). "
                "Glob/Grep may silently fail with spaces. "
                "ALWAYS use: ls -la <directory> | grep <keyword> "
                "or: find <directory> -name '*keyword*' "
                "to discover files with spaces, then Read them with the FULL quoted path."
            )
            _log(f"TRIGGERED: empty result from {tool_name}")
            print(json.dumps({
                "additional_context": hint,
                "followup_message": hint,
            }))
            return

    if tool_name == "Read" and "File not found" in tool_output:
        parts = []
        if "Screenshot" in tool_input or "tmp/" in tool_input:
            parts.append(
                "[File Not Found Fallback] The Read failed. "
                "The user's @-reference path may be missing .png extension or have spaces. "
                "Run: ls -la /Applications/AITerminalTools/tmp/ | grep <keyword> "
                "to find the actual filename, then Read with the correct full path."
            )
        if parts:
            _log(f"TRIGGERED: file not found for {tool_name}")
            print(json.dumps({
                "additional_context": "\n".join(parts),
                "followup_message": "\n".join(parts),
            }))
            return

    print(json.dumps({}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(json.dumps({}))
