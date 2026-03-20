#!/usr/bin/env python3
"""DISABLED: postToolUse hook for USERINPUT reminders.

This hook was disabled in Phase 15 because it injected USERINPUT nagging
messages into additional_context after every tool call, contributing to
the token-burning loop.

USERINPUT compliance is tracked by the brain reflex arc (Dim 3 strategy)
and the .mdc rules, not by Cursor dialog injection.
"""
import json
import sys


def main():
    sys.stdin.read()
    print(json.dumps({}))


if __name__ == "__main__":
    main()
