#!/usr/bin/env python3
"""Pre-commit hook: enforce learned rules for GOOGLE.CDMCP.

Each check function corresponds to a lesson learned from past mistakes.
Run via: python3 tool/GOOGLE.CDMCP/hooks/pre_commit.py [file1 file2 ...]
Without args, checks git-staged files.

Exit codes: 0 = pass, 1 = violations found.
"""

import subprocess
import sys
from pathlib import Path


_TOOL_PREFIX = "tool/GOOGLE.CDMCP/"


def _get_staged_files():
    """Get list of staged files relevant to this tool."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True, text=True)
    return [f for f in result.stdout.strip().split("\n")
            if f.startswith(_TOOL_PREFIX) and f.endswith(".py")]


def check_no_raw_tab_creation(files):
    """Lesson: Never use raw Target.createTarget — use session.require_tab().

    Direct CDP tab creation bypasses session tracking, window targeting,
    and deduplication, causing ghost tabs and duplicate windows.
    """
    errors = []
    for filepath in files:
        try:
            content = Path(filepath).read_text()
        except FileNotFoundError:
            continue
        for i, line in enumerate(content.splitlines(), 1):
            if "Target.createTarget" in line and "session" not in filepath:
                if not line.strip().startswith("#") and not line.strip().startswith("//"):
                    errors.append(f"{filepath}:{i}: Raw Target.createTarget used. "
                                  "Use session.require_tab() instead.")
    return errors


def check_cross_process_state(files):
    """Lesson: In-memory state updates don't cross process boundaries.

    _update_auth_state() only affects the calling process. For cross-process
    persistence, write to a file (e.g., google_identity.json) or use the
    HTTP server.
    """
    errors = []
    for filepath in files:
        if "main.py" not in filepath:
            continue
        try:
            content = Path(filepath).read_text()
        except FileNotFoundError:
            continue
        if "_update_auth_state" in content and "_push_identity_to_server" not in content:
            errors.append(f"{filepath}: Calls _update_auth_state but not "
                          "_push_identity_to_server. State won't persist cross-process.")
    return errors


def check_auth_tab_cleanup_patterns(files):
    """Lesson: Always include RotateCookie and myaccount.google.com in auth tab patterns.

    Google auth flows spawn multiple redirect tabs (RotateCookiesPage,
    myaccount.google.com/?utm_source=sign_in) that must be cleaned up.
    """
    errors = []
    for filepath in files:
        try:
            content = Path(filepath).read_text()
        except FileNotFoundError:
            continue
        if "_AUTH_URL_PATTERNS" in content:
            if "RotateCookie" not in content:
                errors.append(f"{filepath}: _AUTH_URL_PATTERNS missing RotateCookie pattern.")
            if "myaccount.google.com" not in content:
                errors.append(f"{filepath}: _AUTH_URL_PATTERNS missing myaccount.google.com.")
    return errors


_CHECKS = [
    check_no_raw_tab_creation,
    check_cross_process_state,
    check_auth_tab_cleanup_patterns,
]


def main():
    files = sys.argv[1:] if len(sys.argv) > 1 else _get_staged_files()
    if not files:
        return 0

    all_errors = []
    for check in _CHECKS:
        all_errors.extend(check(files))

    if all_errors:
        print(f"\n  CDMCP Pre-commit: {len(all_errors)} violation(s) found:\n")
        for err in all_errors:
            print(f"    - {err}")
        print()
        return 1

    print(f"  CDMCP Pre-commit: {len(files)} file(s) checked, all pass.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
