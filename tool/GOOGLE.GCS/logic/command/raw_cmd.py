#!/usr/bin/env python3
"""GCS --raw / --no-capture command: run commands in Colab with real-time output.

Two variants:
  --raw           Real-time output + result capture. Terminal clears and shows
                  'Finished' when done; clicking Feedback downloads the result.
  --no-capture    Real-time output only, no result file. For pip install or
                  long-running tasks where capturing stdout is impractical.
                  Only the Finished button is shown (no Feedback).
"""
import os
import sys
import time
import hashlib
import json
import shlex
from pathlib import Path
from logic.interface.config import get_color
from logic.interface.turing import ProgressTuringMachine
from logic.interface.turing import TuringStage


def execute(tool, remote_command, state_mgr, load_logic, no_capture=False, no_feedback=False, **kwargs):
    utils = load_logic("utils")

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid)
    current_logical = info.get("current_path", "~") if info else "~"
    remote_cwd = utils.logical_to_mount_path(current_logical)

    remote_root = "/content/drive/MyDrive/REMOTE_ROOT"
    remote_env = "/content/drive/MyDrive/REMOTE_ENV"
    expanded = utils.expand_remote_paths(remote_command, remote_root, remote_env)

    venv_prefix = _get_venv_prefix(state_mgr)
    if venv_prefix:
        expanded = f"{venv_prefix} && {expanded}"

    shell_type = info.get("shell_type", "bash") if info else "bash"
    finished_msg_saved = _t(tool, "remote_finished_result_saved",
                            "Execution completed and result saved. You may now press the Finished button.")
    finished_msg_nc = _t(tool, "remote_finished_no_capture",
                         "(exit code: $?). Press Finished in the GCS window.")
    if no_capture:
        script, metadata = _generate_no_capture_script(tool.project_root, expanded, remote_cwd, shell_type, finished_msg_nc)
    else:
        script, metadata = _generate_raw_script(tool.project_root, expanded, remote_cwd, shell_type, finished_msg_saved)

    mode_tag = "[no-capture]" if no_capture else "[raw]"
    logic_script = Path(__file__).resolve().parent.parent / "executor.py"
    gui_args = [
        "--command", f"{mode_tag} {remote_command}",
        "--script-path", "",
        "--project-root", str(tool.project_root)
    ]
    if no_capture:
        gui_args.append("--no-capture")
    if no_feedback:
        gui_args.append("--no-feedback")

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"
    if cdp_enabled:
        gui_args.append("--cdp-enabled")
    if metadata.get("done_marker"):
        gui_args.extend(["--done-marker", f"GCS_DONE_{metadata['hash']}"])

    command_result = {}
    feedback_mode = [False]

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)

        tmp_script = tool.project_root / "tmp" / f"gcs_raw_{metadata['ts']}_{metadata['hash']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)
        gui_args[3] = str(tmp_script)

        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, str(logic_script), 600,
                args=gui_args, request_id=f"raw_{metadata['ts']}_{metadata['hash']}"
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()

        if res.get("status") == "success":
            if res.get("data") == "Feedback":
                feedback_mode[0] = True
            return True
        status = res.get("status", "error")
        reason = res.get("reason", "")
        if status == "cancelled" or reason in ("interrupted", "signal", "stop"):
            raise KeyboardInterrupt
        if stage:
            _set_failure_reason(stage, res)
        return False

    def verify_action(stage=None):
        if feedback_mode[0]:
            if stage:
                fb_label = _t(tool, "turing_waiting_user_feedback", "Waiting for user feedback")
                stage.active_status = ""
                stage.active_name = fb_label
                stage.bold_part = fb_label
                stage.success_status = ""
                stage.success_name = _t(tool, "turing_received_user_feedback", "Received user feedback")
                stage.refresh()
            feedback_text = _run_userinput_feedback(tool)
            if feedback_text:
                command_result["stdout"] = feedback_text
                command_result["returncode"] = 0
            return True
        import time as _time
        _time.sleep(1.0)
        ok, msg, data = utils.wait_for_gdrive_file(
            tool.project_root, metadata["result_filename"], timeout=60, stage=stage
        )
        if ok:
            command_result.update(data)
            return True
        if stage:
            stage.fail_status = _t(tool, "turing_failed_to_execute", "Failed to execute")
            stage.fail_name = _t(tool, "turing_command", "command")
            stage.error_brief = msg
        return False

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"
    if cdp_enabled:
        waiting_label = _t(tool, "turing_executing_via_cdp", "Executing via CDP...")
    else:
        waiting_label = _t(tool, "turing_waiting_user_action", "Waiting for user action...")
    verifying_label = _t(tool, "turing_verifying_result", "Verifying the command result file...")

    fail_complete = _t(tool, "turing_failed_to_complete", "Failed to complete")
    completed = _t(tool, "turing_completed_user_action", "Completed")
    user_action = _t(tool, "turing_user_action", "user action.")
    remote_exec = _t(tool, "turing_remote_execution", "remote execution.")
    exec_label = remote_exec if cdp_enabled else user_action
    fail_execute = _t(tool, "turing_failed_to_execute", "Failed to execute")
    command_label = _t(tool, "turing_command", "command")
    retrieved = _t(tool, "turing_retrieved_result", "Retrieved")
    exec_result = _t(tool, "turing_execution_result", "execution result.")

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="", active_name=waiting_label,
        fail_status=fail_complete, fail_name=exec_label,
        success_status=completed, success_name=exec_label,
        bold_part=waiting_label
    ))
    if not no_capture:
        pm.add_stage(TuringStage(
            "command execution", verify_action,
            active_status="", active_name=verifying_label,
            fail_status=fail_execute, fail_name=command_label,
            success_status=retrieved, success_name=exec_result,
            bold_part=verifying_label
        ))

    if pm.run(ephemeral=True):
        if no_capture:
            return 0
        if feedback_mode[0]:
            feedback_text = command_result.get("stdout", "")
            if feedback_text:
                print(feedback_text)
            return 0
        if "stdout" in command_result:
            print(command_result["stdout"], end="")
        if "stderr" in command_result and command_result["stderr"]:
            print(f"{get_color('RED')}{command_result['stderr']}{get_color('RESET')}", file=sys.stderr, end="")
        return command_result.get("returncode", 0)

    BOLD = get_color("BOLD")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")
    hint = _t(tool, "hint_drive_not_mounted",
              "If Google Drive is not mounted, run '{bold}GCS --remount{reset}' first.",
              bold=BOLD, reset=RESET)
    print(f"\n{BOLD}{YELLOW}Hint{RESET}: {hint}")
    return 1


def _generate_raw_script(project_root, command, remote_cwd, shell_type="bash", finished_msg=""):
    """Generate a script that shows output in real-time AND captures result to Drive."""
    config_path = project_root / "data" / "config.json"
    mount_hash = ""
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                mount_hash = json.load(f).get("mount_hash", "")
        except:
            pass

    ts = str(int(time.time()))
    cmd_hash = hashlib.md5(f"{ts}_{command}".encode()).hexdigest()[:8]
    script_id = f"{ts}_{cmd_hash}"
    result_filename = f"result_{ts}_{cmd_hash}.json"

    inner_script = f'''#!/bin/bash
if [ ! -d "/content/drive/MyDrive" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Google Drive is not mounted. Run '\\033[1mGCS --remount\\033[0m' locally first."
    exit 1
fi

if [ -n "{mount_hash}" ] && [ ! -f "/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_{mount_hash}" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Mount fingerprint validation failed. Run '\\033[1mGCS --remount\\033[0m' locally to resync."
    exit 1
fi

mkdir -p "{remote_cwd}"
cd "{remote_cwd}"

OUTPUT_FILE="/tmp/gcs_stdout_{script_id}"
ERROR_FILE="/tmp/gcs_stderr_{script_id}"
RESULT_BASE="/content/drive/MyDrive/REMOTE_ROOT/tmp"
mkdir -p "$RESULT_BASE"
RESULT_FILE="$RESULT_BASE/{result_filename}"

SHELL_BIN="{shell_type}"
if [ "{shell_type}" != "bash" ] && [ "{shell_type}" != "sh" ]; then
    CUSTOM_SHELL="/content/drive/MyDrive/REMOTE_ENV/shell/{shell_type}/bin/{shell_type}"
    if [ -x "$CUSTOM_SHELL" ]; then
        SHELL_BIN="$CUSTOM_SHELL"
    elif command -v "{shell_type}" > /dev/null 2>&1; then
        SHELL_BIN="{shell_type}"
    else
        echo "Warning: {shell_type} not found, falling back to bash" >&2
        SHELL_BIN="bash"
    fi
fi

set +e
trap '' PIPE
$SHELL_BIN << 'USER_COMMAND_EOF' > >(tee "$OUTPUT_FILE") 2> >(tee "$ERROR_FILE" >&2)
{command}
USER_COMMAND_EOF
EXIT_CODE=$?
set -e

export GCS_EXIT_CODE=$EXIT_CODE
export GCS_TIMESTAMP="{ts}"
export GCS_COMMAND={shlex.quote(command)}
export GCS_RESULT_FILE="$RESULT_FILE"
export GCS_STDOUT_FILE="$OUTPUT_FILE"
export GCS_STDERR_FILE="$ERROR_FILE"

python3 -c '
import json, os
from datetime import datetime
sf = os.environ["GCS_STDOUT_FILE"]
ef = os.environ["GCS_STDERR_FILE"]
so = open(sf, "r", errors="ignore").read() if os.path.exists(sf) else ""
se = open(ef, "r", errors="ignore").read() if os.path.exists(ef) else ""
r = {{"command": os.environ["GCS_COMMAND"], "stdout": so, "stderr": se, "returncode": int(os.environ["GCS_EXIT_CODE"]), "duration": 0, "timestamp": os.environ["GCS_TIMESTAMP"], "completed": datetime.now().isoformat()}}
with open(os.environ["GCS_RESULT_FILE"], "w") as f: json.dump(r, f, indent=2, ensure_ascii=False)
'

rm -f "$OUTPUT_FILE" "$ERROR_FILE"
clear
echo -e "\\033[1mFinished\\033[0m: {finished_msg}"
'''

    return f'''cat > /tmp/gcs_raw_{script_id}.sh << 'GCS_RAW_EOF'
{inner_script}GCS_RAW_EOF
bash /tmp/gcs_raw_{script_id}.sh ; rm -f /tmp/gcs_raw_{script_id}.sh''', {
        "ts": ts,
        "hash": cmd_hash,
        "result_filename": result_filename
    }


def _generate_no_capture_script(project_root, command, remote_cwd, shell_type="bash", finished_msg=""):
    """Generate a script that runs the command directly without capturing output.

    Output goes straight to the Colab terminal. No temp files, no result JSON.
    Suitable for pip install, long-running tasks, or anything producing large output.
    """
    config_path = project_root / "data" / "config.json"
    mount_hash = ""
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                mount_hash = json.load(f).get("mount_hash", "")
        except:
            pass

    ts = str(int(time.time()))
    cmd_hash = hashlib.md5(f"{ts}_{command}".encode()).hexdigest()[:8]
    script_id = f"{ts}_{cmd_hash}"

    inner_script = f'''#!/bin/bash
if [ ! -d "/content/drive/MyDrive" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Google Drive is not mounted. Run '\\033[1mGCS --remount\\033[0m' locally first."
    exit 1
fi

if [ -n "{mount_hash}" ] && [ ! -f "/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_{mount_hash}" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Mount fingerprint validation failed. Run '\\033[1mGCS --remount\\033[0m' locally to resync."
    exit 1
fi

mkdir -p "{remote_cwd}"
cd "{remote_cwd}"
clear
sleep 0.1
{command}

echo ""
echo -e "\\033[1mFinished\\033[0m: {finished_msg}"
'''

    return f'''cat > /tmp/gcs_nc_{script_id}.sh << 'GCS_NC_EOF'
{inner_script}GCS_NC_EOF
bash /tmp/gcs_nc_{script_id}.sh ; rm -f /tmp/gcs_nc_{script_id}.sh''', {
        "ts": ts,
        "hash": cmd_hash,
        "result_filename": None
    }


def _t(tool, key, default, **kwargs):
    try:
        from logic.interface.lang import get_translation
        logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        return default.format(**kwargs) if kwargs else default


def _run_userinput_feedback(tool):
    """Launch USERINPUT interface to collect direct user feedback."""
    if str(tool.project_root) not in sys.path:
        sys.path.insert(0, str(tool.project_root))
    interface_path = tool.project_root / "tool" / "USERINPUT" / "interface" / "main.py"
    if interface_path.exists():
        try:
            from tool.USERINPUT.interface.main import get_user_feedback
            return get_user_feedback(
                hint="GCS Raw Mode: Please provide feedback on the command output.",
                title="GCS Raw Feedback"
            )
        except Exception:
            pass
    import subprocess, os
    userinput_bin = tool.project_root / "bin" / "USERINPUT" / "USERINPUT"
    if not userinput_bin.exists():
        userinput_bin = tool.project_root / "bin" / "USERINPUT"
    if not userinput_bin.exists():
        return None
    res = subprocess.run(
        [str(userinput_bin), "--hint", "GCS Raw Mode: Please provide feedback on the command output."],
        env={**os.environ, "TK_SILENCE_DEPRECATION": "1"},
        capture_output=True, text=True
    )
    return res.stdout.strip() if res.returncode == 0 else None


def _get_venv_prefix(state_mgr):
    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid) if sid else None
    if not info:
        return None
    venv_name = info.get("venv_name", "base")
    if venv_name and venv_name != "base":
        env_path = f"/content/drive/MyDrive/REMOTE_ENV/venv/{venv_name}"
        return f'export PYTHONPATH="{env_path}:$PYTHONPATH"'
    return None


def _set_failure_reason(stage, res, tool=None):
    status = res.get("status", "error")
    reason = res.get("reason", "")
    if status == "cancelled" or reason in ("interrupted", "signal", "stop"):
        stage.fail_status = _t(tool, "turing_cancelled", "Cancelled") if tool else "Cancelled"
        stage.fail_name = ""
        stage.fail_color = "YELLOW"
        stage.error_brief = _t(tool, "turing_cancelled_by_user", "Cancelled by user.") if tool else "Cancelled by user."
    elif status == "timeout":
        stage.error_brief = _t(tool, "turing_gui_timed_out", "GUI timed out.") if tool else "GUI timed out."
    elif reason == "drive_not_mounted":
        stage.fail_status = _t(tool, "turing_failed_to_execute", "Failed to execute") if tool else "Failed to execute"
        stage.fail_name = _t(tool, "turing_command", "command") if tool else "command"
        stage.error_brief = _t(tool, "turing_drive_not_mounted",
                               "Google Drive not mounted. Run 'GCS --remount' first.") if tool else "Google Drive not mounted. Run 'GCS --remount' first."
    elif reason and reason.startswith("cdp_"):
        stage.error_brief = _t(tool, "turing_cdp_execution_failed", "CDP execution failed.") if tool else "CDP execution failed."
    else:
        stage.error_brief = res.get("message",
                                    _t(tool, "turing_gui_closed_unexpectedly", "GUI closed unexpectedly.") if tool else "GUI closed unexpectedly.")
