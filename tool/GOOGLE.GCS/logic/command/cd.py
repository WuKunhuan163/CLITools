#!/usr/bin/env python3
"""GCS cd command: change remote working directory."""
import sys
import json


def execute(tool, args, state_mgr, load_logic, **kwargs):
    utils = load_logic("utils")

    shell_info = state_mgr.get_shell_info()
    cur_path = shell_info.get("current_path", "~") if shell_info else "~"
    cur_fid = shell_info.get("current_folder_id") if shell_info else None

    if getattr(args, 'force', False):
        return _cd_via_shell(tool, args, state_mgr, load_logic, utils, cur_path)

    folder_id, display_path = utils.resolve_path_via_api(
        tool.project_root, args.path,
        current_path=cur_path, current_folder_id=cur_fid
    )
    if not folder_id:
        import os
        display = args.path
        home = os.path.expanduser("~")
        if display.startswith(home):
            display = "~" + display[len(home):]
        print(f"cd: {display}: No such file or directory", file=sys.stderr)
        return 1

    shell_id = state_mgr.get_active_shell_id()
    state_mgr.update_shell(shell_id, current_path=display_path, current_folder_id=folder_id)
    return 0


def _cd_via_shell(tool, args, state_mgr, load_logic, utils, cur_path):
    """Verify directory exists via remote Colab shell, bypassing API cache."""
    remote_mod = load_logic("command/remote")
    logical = utils.normalize_input_path(args.path, cur_path)
    mount_path = utils.logical_to_mount_path(logical)

    py_cmd = (
        f"import os, json; mount={repr(mount_path)}; "
        f"print(json.dumps({{'exists': os.path.isdir(mount)}}))"
    )

    result = remote_mod.execute(tool, py_cmd, state_mgr, load_logic, as_python=True, capture=True)
    if result is None:
        print("cd --force: remote execution failed.", file=sys.stderr)
        return 1

    output = result.get("stdout", "").strip()
    try:
        data = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        print("cd --force: unexpected remote response.", file=sys.stderr)
        return 1

    if not data.get("exists"):
        import os
        display = args.path
        home = os.path.expanduser("~")
        if display.startswith(home):
            display = "~" + display[len(home):]
        print(f"cd: {display}: No such file or directory (shell verified)", file=sys.stderr)
        return 1

    shell_id = state_mgr.get_active_shell_id()
    state_mgr.update_shell(shell_id, current_path=logical, current_folder_id=None)

    folder_id, _ = utils.resolve_path_via_api(
        tool.project_root, logical, current_path=logical
    )
    if folder_id:
        state_mgr.update_shell(shell_id, current_folder_id=folder_id)

    return 0
