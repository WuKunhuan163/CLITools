#!/usr/bin/env python3
"""GCS edit command: edit remote files via base64-encoded Python script execution."""
import sys
import json
import base64


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    utils = load_logic("utils")

    edit_args = unknown or []
    if not edit_args:
        print("edit: missing operand", file=sys.stderr)
        return 1

    if "--help" in edit_args or "-h" in edit_args:
        _show_help()
        return 0

    preview = False
    backup = False
    positional = []

    for a in edit_args:
        if a == "--preview":
            preview = True
        elif a == "--backup":
            backup = True
        else:
            positional.append(a)

    if len(positional) < 2:
        print("edit: requires <file> <json_spec>", file=sys.stderr)
        print("  json_spec: [[\"old_text\",\"new_text\"], ...]", file=sys.stderr)
        return 1

    filename = positional[0]
    edit_spec_raw = " ".join(positional[1:])

    try:
        replacements = json.loads(edit_spec_raw)
        if not isinstance(replacements, list):
            print("edit: replacement spec must be a JSON array", file=sys.stderr)
            return 1
    except json.JSONDecodeError as e:
        print(f"edit: invalid JSON: {e}", file=sys.stderr)
        return 1

    # Resolve file path to remote mount path
    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    current_path = info.get("current_path", "~") if info else "~"

    logical_path = utils.normalize_input_path(filename, current_path)
    remote_abs_path = utils.logical_to_mount_path(logical_path)

    return _execute_remote_edit(tool, state_mgr, load_logic, utils,
                                filename, remote_abs_path, replacements,
                                preview, backup)


def _execute_remote_edit(tool, state_mgr, load_logic, utils,
                         display_name, remote_path, replacements,
                         preview, backup):
    """Generate a Python edit script, encode with base64, and execute remotely."""
    from logic.interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    script_content = _generate_edit_script(remote_path, replacements, preview, backup)
    script_b64 = base64.b64encode(script_content.encode('utf-8')).decode('ascii')
    command = f"python3 -c \"import base64; exec(base64.b64decode('{script_b64}').decode('utf-8'))\""

    remote_cmd_mod = load_logic("command/remote")
    executor_mod = load_logic("executor")

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    current_logical = info.get("current_path", "~") if info else "~"
    remote_cwd = utils.logical_to_mount_path(current_logical)

    script, metadata = executor_mod.generate_remote_command_script(
        tool.project_root, command, remote_cwd=remote_cwd, as_python=False
    )

    from logic.interface.turing import ProgressTuringMachine
    from logic.interface.turing import TuringStage

    command_result = {}

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)
        logic_script = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic" / "executor.py")

        tmp_script = tool.project_root / "tmp" / f"gcs_edit_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)

        gui_args = [
            "--command", f"edit {display_name}",
            "--script-path", str(tmp_script),
            "--project-root", str(tool.project_root)
        ]
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, logic_script, 600,
                args=gui_args, request_id=f"edit_{metadata['ts']}"
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()
        return res.get("status") == "success"

    def verify_action(stage=None):
        import time
        time.sleep(1.0)
        ok, msg, data = utils.wait_for_gdrive_file(
            tool.project_root, metadata["result_filename"], timeout=60, stage=stage
        )
        if ok:
            command_result.update(data)
            return True
        if stage:
            stage.error_brief = msg
        return False

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="Waiting for", active_name="user action",
        fail_status="Failed", success_status="Completed",
        success_name="user action", bold_part="Waiting for user action"
    ))
    pm.add_stage(TuringStage(
        "edit result", verify_action,
        active_status="Verifying", active_name="edit result",
        fail_status="Failed to verify", success_status="Retrieved",
        success_name="edit result", bold_part="Verifying edit result"
    ))

    if pm.run(ephemeral=True):
        stdout = command_result.get("stdout", "")

        try:
            result = json.loads(stdout.strip())
        except json.JSONDecodeError:
            print(f"{BOLD}{RED}Error{RESET}: Could not parse edit result: {stdout[:200]}", file=sys.stderr)
            return 1

        if not result.get("success"):
            print(f"{BOLD}{RED}Error{RESET}: {result.get('error', 'Edit failed')}", file=sys.stderr)
            return 1

        # Display diff
        diff_lines = result.get("diff_lines", [])
        if diff_lines:
            print(f"\n{BOLD}Edit comparison: {display_name}{RESET}")
            print("=" * 50)
            for line in diff_lines:
                if line.startswith('---') or line.startswith('+++'):
                    continue
                if line.startswith('+'):
                    print(f"{GREEN}{line}{RESET}")
                elif line.startswith('-'):
                    print(f"{RED}{line}{RESET}")
                else:
                    print(line)
            print("=" * 50)

        mode = result.get("mode", "edit")
        if mode == "preview":
            print(f"\n{BOLD}{YELLOW}Preview completed{RESET} (no changes applied).")
        else:
            count = result.get("replacements_made", 0)
            print(f"\n{BOLD}{GREEN}Successfully edited{RESET} {display_name} ({count} replacement(s)).")

        return 0
    return 1


def _generate_edit_script(filename, replacements, preview, backup):
    """Generate the Python script that runs on the remote side."""
    return f"""
import json
import os
import sys
from datetime import datetime
import difflib

def main():
    filename = {json.dumps(filename)}
    replacements = {json.dumps(replacements)}
    preview = {preview}
    backup = {backup}

    try:
        if not os.path.exists(filename):
            print(json.dumps({{"success": False, "error": f"File not found: {{filename}}"}}))
            return

        with open(filename, 'r', encoding='utf-8') as f:
            original_lines = f.readlines()

        modified_lines = list(original_lines)
        applied = 0

        for rep in replacements:
            if not isinstance(rep, list) or len(rep) != 2:
                print(json.dumps({{"success": False, "error": f"Invalid replacement format: {{rep}}"}}))
                return

            source, target = rep

            if isinstance(source, list) and len(source) == 2:
                start, end = source
                if isinstance(start, int) and isinstance(end, int):
                    if 0 <= start < len(modified_lines) and start <= end < len(modified_lines):
                        new_line = target + "\\n" if target and not target.endswith("\\n") else target
                        for j in range(start, end + 1):
                            modified_lines[j] = new_line if j == start else ""
                        applied += 1
                    else:
                        print(json.dumps({{"success": False, "error": f"Line range out of bounds: {{source}}"}}))
                        return
            elif isinstance(source, str):
                found = False
                content = "".join(modified_lines)
                if source in content:
                    content = content.replace(source, target, 1)
                    modified_lines = content.splitlines(keepends=True)
                    found = True
                    applied += 1
                if not found:
                    print(json.dumps({{"success": False, "error": f"String not found: {{source[:80]}}"}}))
                    return

        diff_lines = list(difflib.unified_diff(
            [l.rstrip('\\n') for l in original_lines],
            [l.rstrip('\\n') for l in modified_lines],
            fromfile=f"{{filename}} (original)",
            tofile=f"{{filename}} (modified)",
            lineterm=''
        ))

        if backup and not preview:
            bk = f"{{filename}}.backup.{{datetime.now().strftime('%Y%m%d_%H%M%S')}}"
            with open(bk, 'w', encoding='utf-8') as f:
                f.writelines(original_lines)

        if not preview:
            with open(filename, 'w', encoding='utf-8') as f:
                f.writelines(modified_lines)

        print(json.dumps({{
            "success": True, "replacements_made": applied,
            "diff_lines": diff_lines, "mode": "preview" if preview else "edit"
        }}))

    except Exception as e:
        print(json.dumps({{"success": False, "error": str(e)}}))

if __name__ == "__main__":
    main()
"""
