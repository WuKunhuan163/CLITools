#!/usr/bin/env python3
"""GCS ls command: list remote directory contents."""
import sys
import json
from interface.config import get_color
from interface.turing import ProgressTuringMachine
from interface.turing import TuringStage


def execute(tool, args, state_mgr, load_logic, **kwargs):
    utils = load_logic("utils")

    if getattr(args, 'force', False):
        return _ls_via_shell(tool, args, state_mgr, load_logic, utils)

    return _ls_via_api(tool, args, state_mgr, utils)


def _ls_via_api(tool, args, state_mgr, utils):
    """Standard listing via Drive API."""
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    shell_info = state_mgr.get_shell_info()
    cur_path = shell_info.get("current_path", "~") if shell_info else "~"
    cur_fid = shell_info.get("current_folder_id") if shell_info else None

    ls_path = args.path if args.path is not None else cur_path
    ls_result = {"folder_id": None, "display_path": None, "items": None, "error": None}

    def resolve_stage(stage=None):
        if getattr(args, 'folder_id', None):
            ls_result["folder_id"] = args.folder_id
            ls_result["display_path"] = args.folder_id
            return True
        fid, dpath = utils.resolve_path_via_api(
            tool.project_root, ls_path,
            current_path=cur_path, current_folder_id=cur_fid
        )
        if not fid:
            display = ls_path
            import os
            home = os.path.expanduser("~")
            if display.startswith(home):
                display = "~" + display[len(home):]
            ls_result["error"] = f"ls: cannot access '{display}': No such file or directory"
            if stage:
                stage.error_brief = dpath
            return False
        ls_result["folder_id"] = fid
        ls_result["display_path"] = dpath
        return True

    def list_stage(stage=None):
        ok, items = utils.list_folder_via_api(
            tool.project_root, ls_result["folder_id"],
            long_format=getattr(args, 'l', False)
        )
        if not ok:
            ls_result["error"] = f"ls: {items}"
            if stage:
                stage.error_brief = str(items)
            return False
        ls_result["items"] = items
        return True

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage("resolve path", resolve_stage,
        active_status="Resolving", active_name="remote path",
        fail_status="Failed to resolve", fail_name="path",
        success_status="Resolved", success_name="path",
        stealth=True))
    pm.add_stage(TuringStage("list folder", list_stage,
        active_status="Listing", active_name="folder contents",
        fail_status="Failed to list", fail_name="folder",
        success_status="Listed", success_name="folder",
        stealth=True))

    if pm.run(ephemeral=True):
        items = ls_result["items"]
        display_path = ls_result["display_path"]
        items.sort(key=lambda x: (0 if x["type"] == "folder" else 1, x["name"].lower()))
        if getattr(args, 'l', False):
            print(f"\n{BOLD}{display_path}:{RESET}")
            for item in items:
                name = item["name"] + ("/" if item["type"] == "folder" else "")
                print(f"  {item['id']:<44} {name}")
        else:
            for item in items:
                name = item["name"] + ("/" if item["type"] == "folder" else "")
                print(name)
        return 0
    else:
        print(ls_result.get("error", "ls: unknown error"), file=sys.stderr)
        return 1


def _ls_via_shell(tool, args, state_mgr, load_logic, utils):
    """List directory via remote Colab shell, bypassing API cache."""
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")
    remote_mod = load_logic("command/remote")

    shell_info = state_mgr.get_shell_info()
    cur_path = shell_info.get("current_path", "~") if shell_info else "~"

    ls_path = args.path if args.path is not None else cur_path
    logical = utils.normalize_input_path(ls_path, cur_path)
    mount_path = utils.logical_to_mount_path(logical)
    long_format = getattr(args, 'l', False)

    extra_fields = (
        ", size=os.path.getsize(os.path.join(mount,n)), modified=os.path.getmtime(os.path.join(mount,n))"
        if long_format else ""
    )
    py_cmd = (
        f"import os, json\n"
        f"mount={repr(mount_path)}\n"
        f"if not os.path.isdir(mount):\n"
        f"    print(json.dumps({{'error': 'ls: cannot access {logical}: No such file or directory'}}))\n"
        f"else:\n"
        f"    items=[dict(name=n, type='folder' if os.path.isdir(os.path.join(mount,n)) else 'file'"
        f"{extra_fields}) for n in sorted(os.listdir(mount))]\n"
        f"    print(json.dumps({{'items': items}}))"
    )

    result = remote_mod.execute(tool, py_cmd, state_mgr, load_logic, as_python=True, capture=True)
    if result is None:
        print("ls --force: remote execution failed.", file=sys.stderr)
        return 1

    output = result.get("stdout", "").strip()
    if not output:
        print("ls --force: no output from remote.", file=sys.stderr)
        return 1

    try:
        data = json.loads(output)
    except json.JSONDecodeError:
        for line in output.split("\n"):
            print(line)
        return 0

    if "error" in data:
        print(data["error"], file=sys.stderr)
        return 1

    items = data.get("items", [])
    items.sort(key=lambda x: (0 if x["type"] == "folder" else 1, x["name"].lower()))

    if long_format:
        import time as _time
        print(f"\n{BOLD}{logical} (shell):{RESET}")
        for item in items:
            name = item["name"] + ("/" if item["type"] == "folder" else "")
            size = item.get("size", "")
            mtime = item.get("modified")
            ts = _time.strftime("%Y-%m-%d %H:%M", _time.localtime(mtime)) if mtime else ""
            size_str = f"{size:>10}" if size != "" else f"{'':>10}"
            print(f"  {size_str}  {ts}  {name}")
    else:
        for item in items:
            name = item["name"] + ("/" if item["type"] == "folder" else "")
            print(name)

    return 0
