#!/usr/bin/env python3
"""GCS bg command: run remote commands in background with status tracking."""
import os
import sys
import json
import time
import base64
import hashlib
import random
from pathlib import Path

REMOTE_TMP = "/content/drive/MyDrive/REMOTE_ROOT/tmp"

BG_STATUS_TEMPLATE = "cmd_bg_{pid}.status"
BG_SCRIPT_TEMPLATE = "cmd_bg_{pid}.sh"
BG_LOG_TEMPLATE = "cmd_bg_{pid}.log"
BG_RESULT_TEMPLATE = "cmd_bg_{pid}.result.json"


def execute(tool, args, state_mgr, load_logic, unknown=None, **kwargs):
    bg_args = unknown or []

    if not bg_args or "--help" in bg_args or "-h" in bg_args:
        _show_help()
        return 0

    utils = load_logic("utils")

    if bg_args[0] == "--status":
        task_id = bg_args[1] if len(bg_args) > 1 else None
        return _bg_status(tool, state_mgr, load_logic, utils, task_id)

    elif bg_args[0] == "--log":
        if len(bg_args) < 2:
            print("bg: --log requires a task ID", file=sys.stderr)
            return 1
        return _bg_log(tool, state_mgr, load_logic, utils, bg_args[1])

    elif bg_args[0] == "--result":
        if len(bg_args) < 2:
            print("bg: --result requires a task ID", file=sys.stderr)
            return 1
        return _bg_result(tool, state_mgr, load_logic, utils, bg_args[1])

    elif bg_args[0] == "--cleanup":
        task_id = bg_args[1] if len(bg_args) > 1 else None
        return _bg_cleanup(tool, state_mgr, load_logic, utils, task_id)

    elif bg_args[0].startswith("--"):
        print(f"bg: unknown option '{bg_args[0]}'", file=sys.stderr)
        return 1

    else:
        command = " ".join(bg_args)
        return _bg_submit(tool, state_mgr, load_logic, utils, command)


def _bg_submit(tool, state_mgr, load_logic, utils, command):
    """Submit a command for background execution."""
    from logic.interface.config import get_color
    GREEN, BOLD, RESET = get_color("GREEN"), get_color("BOLD"), get_color("RESET")

    bg_pid = f"{int(time.time())}_{random.randint(1000, 9999)}"
    start_time_iso = time.strftime("%Y-%m-%dT%H:%M:%S")

    status_file = BG_STATUS_TEMPLATE.format(pid=bg_pid)
    script_file = BG_SCRIPT_TEMPLATE.format(pid=bg_pid)
    log_file = BG_LOG_TEMPLATE.format(pid=bg_pid)
    result_file = BG_RESULT_TEMPLATE.format(pid=bg_pid)

    cmd_b64 = base64.b64encode(command.encode("utf-8")).decode("ascii")

    result_writer = _generate_result_writer()
    writer_b64 = base64.b64encode(result_writer.encode("utf-8")).decode("ascii")

    cmd_display = command.replace('"', '\\"').replace("'", "'\\''")[:200]

    bootstrap = f"""
mkdir -p {REMOTE_TMP}

# Write initial status using a temp file approach (avoids quoting issues)
python3 -c "
import json
with open('{REMOTE_TMP}/{status_file}', 'w') as f:
    json.dump({{'pid': '{bg_pid}', 'command': '{cmd_display}', 'status': 'starting', 'start_time': '{start_time_iso}'}}, f, indent=2)
" 2>/dev/null

# Create execution script in /tmp (local, no Drive FUSE delay)
echo '{cmd_b64}' | base64 -d > /tmp/bg_user_cmd_{bg_pid}.sh
echo '{writer_b64}' | base64 -d > /tmp/bg_writer_{bg_pid}.py

cat > /tmp/bg_exec_{bg_pid}.sh << 'BGEOF'
#!/bin/bash
sleep 2
echo "[$(date +%H:%M:%S)] Background task started (PID: $$)"

# Execute the user command
bash /tmp/bg_user_cmd_{bg_pid}.sh > /tmp/bg_stdout_{bg_pid} 2> /tmp/bg_stderr_{bg_pid}
EXIT_CODE=$?
echo "[$(date +%H:%M:%S)] Command completed with exit code: $EXIT_CODE"

# Write result file to Drive
python3 /tmp/bg_writer_{bg_pid}.py \\
  {REMOTE_TMP}/{result_file} \\
  $EXIT_CODE \\
  /tmp/bg_stdout_{bg_pid} \\
  /tmp/bg_stderr_{bg_pid}

# Update status to completed
python3 -c "
import json
from datetime import datetime
with open('{REMOTE_TMP}/{status_file}', 'w') as f:
    json.dump({{'pid': '{bg_pid}', 'command': '{cmd_display}', 'status': 'completed', 'start_time': '{start_time_iso}', 'end_time': datetime.now().isoformat(), 'exit_code': $EXIT_CODE, 'result_file': '{result_file}'}}, f, indent=2)
"

# Clean up temp files
rm -f /tmp/bg_user_cmd_{bg_pid}.sh /tmp/bg_stdout_{bg_pid} /tmp/bg_stderr_{bg_pid}
rm -f /tmp/bg_writer_{bg_pid}.py /tmp/bg_exec_{bg_pid}.sh

echo "[$(date +%H:%M:%S)] Background task finished"
BGEOF

chmod +x /tmp/bg_exec_{bg_pid}.sh

# Launch in background (script runs from /tmp, writes results to Drive)
(nohup /tmp/bg_exec_{bg_pid}.sh > {REMOTE_TMP}/{log_file} 2>&1) &
REAL_PID=$!

# Update status with real PID
python3 -c "
import json
with open('{REMOTE_TMP}/{status_file}', 'w') as f:
    json.dump({{'pid': '{bg_pid}', 'command': '{cmd_display}', 'status': 'running', 'start_time': '{start_time_iso}', 'real_pid': $REAL_PID, 'result_file': '{result_file}'}}, f, indent=2)
"

echo "Background task launched (PID: $REAL_PID)"
"""

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, bootstrap.strip())
    if ok:
        exit_code = result.get("exit_code", result.get("returncode", 0))
        stdout = result.get("stdout", "")
        if exit_code == 0:
            print(f"\n{BOLD}{GREEN}Background task submitted{RESET}")
            print(f"  Task ID: {bg_pid}")
            print(f"  Command: {command[:60]}{'...' if len(command) > 60 else ''}")
            print()
            print("Track with:")
            print(f"  GCS bg --status {bg_pid}    Check status")
            print(f"  GCS bg --log {bg_pid}       View output log")
            print(f"  GCS bg --result {bg_pid}    View result")
            print(f"  GCS bg --cleanup {bg_pid}   Clean up files")
            return 0
        if stdout:
            print(stdout, end="")

    print("Error: failed to submit background task.", file=sys.stderr)
    return 1


def _bg_status(tool, state_mgr, load_logic, utils, task_id=None):
    """Show status of background task(s)."""
    from logic.interface.config import get_color
    GREEN, RED, YELLOW, BOLD, RESET = (
        get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("BOLD"), get_color("RESET")
    )

    if task_id:
        status_file = BG_STATUS_TEMPLATE.format(pid=task_id)
        return _read_and_show_remote_file(
            tool, state_mgr, load_logic, utils,
            f"cat {REMOTE_TMP}/{status_file} 2>/dev/null || echo 'NOT_FOUND'",
            f"Status for task {task_id}",
            lambda content: _format_single_status(content, task_id, GREEN, RED, YELLOW, BOLD, RESET)
        )
    else:
        cmd = f"""
ls {REMOTE_TMP}/cmd_bg_*.status 2>/dev/null | while read f; do
    BG_PID=$(basename "$f" .status | sed 's/cmd_bg_//')
    STATUS=$(python3 -c "import json; d=json.load(open('$f')); print(d.get('status','unknown'))" 2>/dev/null || echo "unknown")
    CMD=$(python3 -c "import json; c=json.load(open('$f')).get('command','?'); print(c[:30])" 2>/dev/null || echo "?")
    echo "$BG_PID|$STATUS|$CMD"
done
"""
        return _read_and_show_remote_file(
            tool, state_mgr, load_logic, utils, cmd.strip(),
            "Background tasks",
            lambda content: _format_task_list(content, GREEN, RED, YELLOW, BOLD, RESET)
        )


def _bg_log(tool, state_mgr, load_logic, utils, task_id):
    """Show log of a background task."""
    log_file = BG_LOG_TEMPLATE.format(pid=task_id)
    cmd = f'cat {REMOTE_TMP}/{log_file} 2>/dev/null || echo "Log file not found for task {task_id}"'
    return _read_and_show_remote_file(
        tool, state_mgr, load_logic, utils, cmd,
        f"Log for task {task_id}",
        lambda content: print(content.rstrip())
    )


def _bg_result(tool, state_mgr, load_logic, utils, task_id):
    """Show result of a background task."""
    from logic.interface.config import get_color
    GREEN, RED, BOLD, RESET = get_color("GREEN"), get_color("RED"), get_color("BOLD"), get_color("RESET")

    result_file = BG_RESULT_TEMPLATE.format(pid=task_id)
    cmd = f'cat {REMOTE_TMP}/{result_file} 2>/dev/null || echo "NOT_FOUND"'

    def format_result(content):
        content = content.strip()
        if content == "NOT_FOUND":
            print(f"Result file not found for task {task_id}.")
            print(f"Use 'GCS bg --status {task_id}' to check if it's still running.")
            return

        try:
            data = json.loads(content)
            success = data.get("success", False)
            result_data = data.get("data", {})
            exit_code = result_data.get("exit_code", -1)

            status_color = GREEN if success else RED
            print(f"{BOLD}Result for task {task_id}:{RESET}")
            print(f"  Success: {status_color}{success}{RESET}")
            print(f"  Exit code: {exit_code}")

            stdout = result_data.get("stdout", "").strip()
            stderr = result_data.get("stderr", "").strip()
            if stdout:
                print(f"\n{BOLD}stdout:{RESET}")
                for line in stdout.split("\n"):
                    print(f"  {line}")
            if stderr:
                print(f"\n{BOLD}{RED}stderr:{RESET}")
                for line in stderr.split("\n"):
                    print(f"  {RED}{line}{RESET}")
        except json.JSONDecodeError:
            print(f"Raw result: {content[:500]}")

    return _read_and_show_remote_file(
        tool, state_mgr, load_logic, utils, cmd,
        f"Result for task {task_id}", format_result
    )


def _bg_cleanup(tool, state_mgr, load_logic, utils, task_id=None):
    """Clean up background task files."""
    from logic.interface.config import get_color
    GREEN, BOLD, RESET = get_color("GREEN"), get_color("BOLD"), get_color("RESET")

    if task_id:
        patterns = [
            BG_STATUS_TEMPLATE.format(pid=task_id),
            BG_SCRIPT_TEMPLATE.format(pid=task_id),
            BG_LOG_TEMPLATE.format(pid=task_id),
            BG_RESULT_TEMPLATE.format(pid=task_id),
        ]
        rm_cmds = [f'rm -f {REMOTE_TMP}/{p}' for p in patterns]
        cmd = " && ".join(rm_cmds) + f' && echo "Cleaned up task {task_id}"'
    else:
        cmd = f"""
CLEANED=0
for f in {REMOTE_TMP}/cmd_bg_*.status; do
    [ -f "$f" ] || continue
    STATUS=$(python3 -c "import json; print(json.load(open('$f')).get('status',''))" 2>/dev/null)
    if [ "$STATUS" = "completed" ]; then
        BG_PID=$(basename "$f" .status | sed 's/cmd_bg_//')
        rm -f {REMOTE_TMP}/cmd_bg_${{BG_PID}}.*
        CLEANED=$((CLEANED + 1))
    fi
done
echo "Cleaned up $CLEANED completed task(s)"
"""

    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, cmd.strip())
    if ok:
        stdout = result.get("stdout", "").strip()
        if stdout:
            print(f"{BOLD}{GREEN}{stdout}{RESET}")
        return 0
    print("Error: cleanup failed.", file=sys.stderr)
    return 1


def _run_remote_cmd(tool, state_mgr, load_logic, utils, command):
    """Execute a remote command. Returns (success, result_dict)."""
    executor_mod = load_logic("executor")

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid)
    current_logical = info.get("current_path", "~") if info else "~"
    remote_cwd = utils.logical_to_mount_path(current_logical)

    remote_root = "/content/drive/MyDrive/REMOTE_ROOT"
    remote_env = "/content/drive/MyDrive/REMOTE_ENV"
    expanded = utils.expand_remote_paths(command, remote_root, remote_env)

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"
    script, metadata = executor_mod.generate_remote_command_script(
        tool.project_root, expanded, remote_cwd=remote_cwd, as_python=False,
        cdp_mode=cdp_enabled
    )

    command_result = {}

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)
        logic_script = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic" / "executor.py")

        tmp_script = tool.project_root / "tmp" / f"gcs_bg_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)

        gui_args = [
            "--command", "bg operation",
            "--script-path", str(tmp_script),
            "--project-root", str(tool.project_root)
        ]
        if cdp_enabled:
            gui_args.append("--as-python")
        if metadata.get("done_marker"):
            gui_args.extend(["--done-marker", metadata["done_marker"]])
        if cdp_enabled:
            gui_args.append("--cdp-enabled")
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, logic_script, 600,
                args=gui_args, request_id=f"bg_{metadata['ts']}"
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()
        return res.get("status") == "success"

    def verify_action(stage=None):
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

    from logic.interface.turing import ProgressTuringMachine
    from logic.interface.turing import TuringStage

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="Waiting for", active_name="user action",
        fail_status="Failed", success_status="Completed",
        success_name="user action", bold_part="Waiting for user action"
    ))
    pm.add_stage(TuringStage(
        "command result", verify_action,
        active_status="Verifying", active_name="result",
        fail_status="Failed to verify", success_status="Retrieved",
        success_name="result", bold_part="Verifying result"
    ))

    if pm.run(ephemeral=True):
        return True, command_result
    return False, {}


def _read_and_show_remote_file(tool, state_mgr, load_logic, utils, cmd, desc, formatter):
    """Run a remote command and pass its stdout to a formatter function."""
    ok, result = _run_remote_cmd(tool, state_mgr, load_logic, utils, cmd)
    if ok:
        stdout = result.get("stdout", "")
        formatter(stdout)
        return 0
    print(f"Error: failed to retrieve {desc}.", file=sys.stderr)
    return 1


def _format_single_status(content, task_id, GREEN, RED, YELLOW, BOLD, RESET):
    content = content.strip()
    if content == "NOT_FOUND":
        print(f"Task {task_id} not found.")
        return

    try:
        data = json.loads(content)
        status = data.get("status", "unknown")
        cmd = data.get("command", "?")
        start = data.get("start_time", "?")

        colors = {"starting": YELLOW, "running": YELLOW, "completed": GREEN}
        sc = colors.get(status, RED)

        print(f"{BOLD}Task {task_id}:{RESET}")
        print(f"  Status:  {sc}{status}{RESET}")
        print(f"  Command: {cmd[:60]}{'...' if len(cmd) > 60 else ''}")
        print(f"  Started: {start}")

        if status == "completed":
            print(f"  Ended:   {data.get('end_time', '?')}")
            print(f"  Exit:    {data.get('exit_code', '?')}")
            print(f"  Result:  {data.get('result_file', '?')}")
        elif status == "running":
            real_pid = data.get("real_pid", "?")
            print(f"  PID:     {real_pid}")
    except json.JSONDecodeError:
        print(f"Raw status: {content[:300]}")


def _format_task_list(content, GREEN, RED, YELLOW, BOLD, RESET):
    content = content.strip()
    if not content:
        print("No background tasks found.")
        return

    lines = [l.strip() for l in content.split("\n") if l.strip()]
    if not lines:
        print("No background tasks found.")
        return

    colors = {"starting": YELLOW, "running": YELLOW, "completed": GREEN}
    print(f"{BOLD}{'Task ID':<20} {'Status':<12} Command{RESET}")
    print(f"{'-'*20} {'-'*12} {'-'*30}")
    for line in lines:
        parts = line.split("|", 2)
        if len(parts) == 3:
            tid, status, cmd = parts
            sc = colors.get(status, RED)
            print(f"{tid:<20} {sc}{status:<12}{RESET} {cmd}")


def _generate_result_writer():
    """Python script that writes the result JSON on the remote."""
    return """
import json, sys, os
from datetime import datetime

result_file = sys.argv[1]
exit_code = int(sys.argv[2])
stdout_file = sys.argv[3]
stderr_file = sys.argv[4]

stdout = ""
stderr = ""
if os.path.exists(stdout_file):
    with open(stdout_file, "r") as f:
        stdout = f.read()
if os.path.exists(stderr_file):
    with open(stderr_file, "r") as f:
        stderr = f.read()

result = {
    "success": exit_code == 0,
    "data": {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "working_dir": os.getcwd(),
        "timestamp": datetime.now().isoformat(),
        "end_time": datetime.now().isoformat()
    }
}

with open(result_file, "w") as f:
    json.dump(result, f, indent=2, ensure_ascii=False)
"""


def _show_help():
    print("""bg - run remote commands in background with status tracking

Usage:
  GCS bg <command>                       Run command in background
  GCS bg --status [task_id]              Show task status (all or specific)
  GCS bg --log <task_id>                 View task output log
  GCS bg --result <task_id>              View task result (stdout/stderr)
  GCS bg --cleanup [task_id]             Clean up completed task files

Description:
  Execute long-running commands (pip install, git clone, etc.) in
  the background without blocking. Track progress via status files
  stored in ~/tmp/ on the remote.

Workflow:
  1. Submit:  GCS bg "pip install torch"
  2. Check:   GCS bg --status <task_id>
  3. View:    GCS bg --log <task_id>
  4. Result:  GCS bg --result <task_id>
  5. Cleanup: GCS bg --cleanup <task_id>

Examples:
  GCS bg "pip install numpy pandas"      Install packages in background
  GCS bg "git clone https://..."         Clone repo in background
  GCS bg --status                        List all background tasks
  GCS bg --cleanup                       Clean up all completed tasks""")
