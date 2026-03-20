#!/usr/bin/env python3
"""GCS pwd command: print current remote working directory."""


def execute(tool, args, state_mgr, load_logic, **kwargs):
    shell_info = state_mgr.get_shell_info()
    current_path = shell_info.get("current_path", "~") if shell_info else "~"
    print(current_path)
    return 0
