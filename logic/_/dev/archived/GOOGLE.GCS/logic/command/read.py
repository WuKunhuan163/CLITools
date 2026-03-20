#!/usr/bin/env python3
"""GCS read command: display remote file content with line numbers."""
import sys


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    utils = load_logic("utils")

    file_args = unknown or []
    if not file_args:
        print("read: missing operand", file=sys.stderr)
        return 1

    force = False
    path = None
    start_line = None
    end_line = None

    positional = []
    for a in file_args:
        if a == "--force":
            force = True
        elif a in ("--help", "-h"):
            _show_help()
            return 0
        else:
            positional.append(a)

    if not positional:
        print("read: missing file operand", file=sys.stderr)
        return 1

    path = positional[0]
    if len(positional) >= 2:
        try:
            start_line = int(positional[1])
        except ValueError:
            pass
    if len(positional) >= 3:
        try:
            end_line = int(positional[2])
        except ValueError:
            pass

    if force:
        return _read_via_remote(tool, path, state_mgr, load_logic, utils, start_line, end_line)
    return _read_via_api(tool, path, state_mgr, load_logic, utils, start_line, end_line)


def _read_via_api(tool, path, state_mgr, load_logic, utils, start_line=None, end_line=None):
    folder_id, filename, display = utils.resolve_file_path(
        tool.project_root, path, state_mgr, load_logic
    )
    if not folder_id:
        print(f"read: {filename}", file=sys.stderr)
        return 1

    ok, data = utils.read_file_via_api(tool.project_root, folder_id, filename)
    if not ok:
        print(f"read: {path}: {data.get('error', 'Unknown error')}", file=sys.stderr)
        return 1

    _print_with_line_numbers(data.get("content", ""), start_line, end_line)
    return 0


def _read_via_remote(tool, path, state_mgr, load_logic, utils, start_line=None, end_line=None):
    """Read file via remote cat command (bypasses Drive API cache)."""
    remote_cmd_mod = load_logic("command/remote")
    mount_path = _resolve_to_mount_path(path, state_mgr, utils)
    cat_command = f'cat "{mount_path}"'

    result = remote_cmd_mod.execute(tool, cat_command, state_mgr, load_logic, capture=True)
    if result is None:
        print(f"read --force: {path}: failed to read via remote", file=sys.stderr)
        return 1
    content = result.get("stdout", "")
    if result.get("returncode", 1) != 0:
        stderr = result.get("stderr", "")
        print(f"read --force: {path}: {stderr or 'command failed'}", file=sys.stderr)
        return 1
    _print_with_line_numbers(content, start_line, end_line)
    return 0


def _resolve_to_mount_path(path, state_mgr, utils):
    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    current_path = info.get("current_path", "~") if info else "~"
    logical = utils.normalize_input_path(path, current_path)
    return utils.logical_to_mount_path(logical)


def _print_with_line_numbers(content, start_line=None, end_line=None):
    lines = content.split('\n')
    total = len(lines)
    width = len(str(total))

    if start_line is not None:
        start_idx = max(0, start_line - 1)
    else:
        start_idx = 0

    if end_line is not None:
        end_idx = min(total, end_line)
    else:
        end_idx = total

    for i in range(start_idx, end_idx):
        print(f"{i + 1:{width}}: {lines[i]}")


def _show_help():
    print("""read - display remote file contents with line numbers

Usage:
  GCS read <file> [start] [end] [--force]

Arguments:
  file                     Remote file path (~/..., @/..., or relative)
  start                    Starting line number (optional)
  end                      Ending line number (optional)

Options:
  --force                  Read via remote cat command (bypasses API cache)
  -h, --help               Show this help message

Examples:
  GCS read ~/tmp/script.py           Display entire file with line numbers
  GCS read ~/tmp/script.py 10 20     Display lines 10-20
  GCS read --force config.json       Force re-read bypassing cache""")
