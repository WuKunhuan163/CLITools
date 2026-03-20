#!/usr/bin/env python3
"""DISABLED: stop hook for USERINPUT enforcement.

This hook was disabled in Phase 15 because it auto-injected followup_message
into the Cursor dialog every time the assistant stopped, creating a toxic
infinite loop that burned 35.9M tokens.

USERINPUT enforcement is now handled by:
- Brain reflex arc: userinput_after_task strategy
- .mdc rules: Cursor rules that guide the AI
- Evaluator: Compliance tracking in brain/src/evaluator.py

The Cursor dialog injection mechanism is strictly prohibited.
"""
import json
import sys


def main():
    # Read stdin (required by hook protocol) but return empty output
    sys.stdin.read()
    print(json.dumps({}))


if __name__ == "__main__":
    main()
