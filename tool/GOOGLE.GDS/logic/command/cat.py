#!/usr/bin/env python3
"""GDS cat command: display content of a remote file."""
import sys


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    utils = load_logic("utils")

    file_args = unknown or []
    if not file_args:
        print("cat: missing operand", file=sys.stderr)
        return 1

    force = False
    path = None
    for a in file_args:
        if a == "--force":
            force = True
        elif a in ("--help", "-h"):
            _show_help()
            return 0
        elif path is None:
            path = a

    if not path:
        print("cat: missing file operand", file=sys.stderr)
        return 1

    if force:
        return _cat_via_remote(tool, path, state_mgr, load_logic, utils)
    return _cat_via_api(tool, path, state_mgr, load_logic, utils)


def _cat_via_api(tool, path, state_mgr, load_logic, utils):
    folder_id, filename, display = utils.resolve_file_path(
        tool.project_root, path, state_mgr, load_logic
    )
    if not folder_id:
        print(f"cat: {filename}", file=sys.stderr)
        return 1

    ok, data = utils.read_file_via_api(tool.project_root, folder_id, filename)
    if not ok:
        print(f"cat: {path}: {data.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    print(data.get("content", ""), end="")
    return 0


def _cat_via_remote(tool, path, state_mgr, load_logic, utils):
    """Read file via remote cat command (bypasses Drive API cache)."""
    remote_cmd_mod = load_logic("command/remote")
    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    current_path = info.get("current_path", "~") if info else "~"
    logical = utils.normalize_input_path(path, current_path)
    mount_path = utils.logical_to_mount_path(logical)
    cat_command = f'cat "{mount_path}"'

    result = remote_cmd_mod.execute(tool, cat_command, state_mgr, load_logic, capture=True)
    if result is None:
        print(f"cat --force: {path}: failed to read via remote", file=sys.stderr)
        return 1
    content = result.get("stdout", "")
    if result.get("returncode", 1) != 0:
        stderr = result.get("stderr", "")
        print(f"cat --force: {path}: {stderr or 'command failed'}", file=sys.stderr)
        return 1
    print(content, end="")
    return 0


def _show_help():
    print("""cat - display content of a remote file

Usage:
  GDS cat <file> [--force]

Arguments:
  file                     Remote file path (~/..., @/..., or relative)

Options:
  --force                  Read via remote cat command (bypasses API cache)
  -h, --help               Show this help message

Examples:
  GDS cat ~/tmp/script.py             Display file content
  GDS cat @/config/settings.json      Display env config file
  GDS cat --force ~/data/output.txt   Force read bypassing cache""")
