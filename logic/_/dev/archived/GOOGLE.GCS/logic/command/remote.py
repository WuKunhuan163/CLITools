#!/usr/bin/env python3
"""GCS remote command execution: send bash/Python commands to Colab via GUI."""
import os
import sys
from pathlib import Path
from interface.config import get_color
from interface.turing import ProgressTuringMachine
from interface.turing import TuringStage


def _t(tool, key, default, **kwargs):
    """Get GCS translated string."""
    try:
        from interface.lang import get_translation
        logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        return default.format(**kwargs) if kwargs else default


def execute(tool, remote_command, state_mgr, load_logic, as_python=False, capture=False, no_feedback=False, **kwargs):
    import time as _time_mod

    gcs_logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
    if gcs_logic_dir not in sys.path:
        sys.path.insert(0, gcs_logic_dir)
    from reconnection_manager import (
        should_remount_before_command, should_remount_after_command,
        increment_execution_counter, set_remount_required_flag,
        clear_remount_required_flag, reset_execution_counter,
        is_remount_in_progress, wait_for_remount_completion,
    )

    if is_remount_in_progress(tool.project_root):
        wait_for_remount_completion(tool.project_root, max_wait=120)

    needs, reason = should_remount_before_command(tool.project_root)
    if needs:
        remount_mod_cmd = load_logic("command/remount_cmd")
        remount_mod_cmd.execute(tool, None, state_mgr, load_logic)
        clear_remount_required_flag(tool.project_root)
        reset_execution_counter(tool.project_root)

    _cmd_start_time = _time_mod.time()

    executor_mod = load_logic("executor")
    utils = load_logic("utils")

    sid = state_mgr.get_active_shell_id()
    info = state_mgr.get_shell_info(sid)
    current_logical = info.get("current_path", "~") if info else "~"
    remote_cwd = utils.logical_to_mount_path(current_logical)

    remote_root = "/content/drive/MyDrive/REMOTE_ROOT"
    remote_env = "/content/drive/MyDrive/REMOTE_ENV"
    expanded_command = utils.expand_remote_paths(remote_command, remote_root, remote_env)

    venv_prefix = _get_venv_prefix(state_mgr)
    if venv_prefix and not as_python:
        expanded_command = f"{venv_prefix} && {expanded_command}"

    shell_type = info.get("shell_type", "bash") if info else "bash"
    finished_msg = _t(tool, "remote_finished_result_saved",
                       "Execution completed and result saved. You may now press the Finished button.")
    executing_msg = _t(tool, "remote_executing", "Executing")
    finished_label = _t(tool, "gui_title_remote_command", "GCS Remote Command")

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"

    if cdp_enabled:
        mount_ok = _verify_mount_precheck(tool, utils)
        if not mount_ok:
            BOLD = get_color("BOLD")
            BLUE = get_color("BLUE")
            RESET = get_color("RESET")
            print(f"{BOLD}{BLUE}{_t(tool, 'turing_auto_remounting', 'Auto-remounting Google Drive...')}{RESET}")
            remount_mod_cmd = load_logic("command/remount_cmd")
            rc = remount_mod_cmd.execute(tool, None, state_mgr, load_logic, no_feedback=no_feedback)
            if rc != 0:
                print(f"{get_color('BOLD')}{get_color('RED')}"
                      f"{_t(tool, 'turing_failed_to_remount', 'Failed to remount')}{get_color('RESET')} "
                      f"Google Drive. {_t(tool, 'hint_run_remount_manually', 'Run GCS --remount manually.')}")
                return 1 if not capture else None

    script, metadata = executor_mod.generate_remote_command_script(
        tool.project_root, expanded_command, remote_cwd=remote_cwd, as_python=as_python,
        shell_type=shell_type, finished_msg=finished_msg,
        executing_msg=executing_msg, finished_label=finished_label,
        cdp_mode=cdp_enabled
    )
    home = os.path.expanduser("~")
    display_command = remote_command.replace(home, "~") if home != "~" else remote_command

    logic_script = Path(__file__).resolve().parent.parent / "executor.py"
    gui_args = [
        "--command", display_command,
        "--script-path", "",
        "--project-root", str(tool.project_root)
    ]
    if as_python or cdp_enabled:
        gui_args.append("--as-python")
    if metadata.get("done_marker"):
        gui_args.extend(["--done-marker", metadata["done_marker"]])
    if cdp_enabled:
        gui_args.append("--cdp-enabled")
    if no_feedback:
        gui_args.append("--no-feedback")

    command_result = {}

    feedback_mode = [False]

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)

        tmp_script = tool.project_root / "tmp" / f"gcs_cmd_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)
        gui_args[3] = str(tmp_script)
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, str(logic_script), 600,
                args=gui_args, request_id=f"cmd_{metadata['ts']}"
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
            _set_failure_reason(stage, res, tool=tool)
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
        import time
        time.sleep(1.0)
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

    def on_failure():
        pass

    if cdp_enabled:
        waiting_label = _t(tool, "turing_executing_via_cdp", "Executing via CDP...")
    else:
        waiting_label = _t(tool, "turing_waiting_user_action", "Waiting for user action...")
    verifying_label = _t(tool, "turing_verifying_result", "Verifying the command result file...")

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GOOGLE.GCS", log_dir=tool.get_log_dir())
    fail_complete_label = _t(tool, "turing_failed_to_complete", "Failed to complete")
    completed_label = _t(tool, "turing_completed_user_action", "Completed")
    user_action_label = _t(tool, "turing_user_action", "user action.")
    fail_execute_label = _t(tool, "turing_failed_to_execute", "Failed to execute")
    retrieved_label = _t(tool, "turing_retrieved_result", "Retrieved")
    exec_result_label = _t(tool, "turing_execution_result", "execution result.")
    command_label = _t(tool, "turing_command", "command")
    if cdp_enabled:
        exec_stage_label = _t(tool, "turing_remote_execution", "remote execution.")
    else:
        exec_stage_label = user_action_label

    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="", active_name=waiting_label,
        fail_status=fail_complete_label, fail_name=exec_stage_label,
        success_status=completed_label,
        success_name=exec_stage_label, bold_part=waiting_label
    ))
    pm.add_stage(TuringStage(
        "command execution", verify_action,
        active_status="", active_name=verifying_label,
        fail_status=fail_execute_label, fail_name=command_label,
        success_status=retrieved_label, success_name=exec_result_label,
        bold_part=verifying_label
    ))

    success = pm.run(ephemeral=True)

    _cmd_elapsed = _time_mod.time() - _cmd_start_time
    increment_execution_counter(tool.project_root)
    post_needs, post_reason = should_remount_after_command(tool.project_root, _cmd_elapsed)
    if post_needs:
        set_remount_required_flag(tool.project_root, post_reason)

    if success:
        if feedback_mode[0]:
            feedback_text = command_result.get("stdout", "")
            if feedback_text and not capture:
                print(feedback_text)
            return 0 if not capture else command_result
        if capture:
            return command_result
        if "stdout" in command_result:
            print(command_result["stdout"], end="")
        if "stderr" in command_result and command_result["stderr"]:
            print(f"{get_color('RED')}{command_result['stderr']}{get_color('RESET')}", file=sys.stderr, end="")
        return command_result.get("returncode", 0)
    on_failure()
    if capture:
        return None
    return 1


def _run_userinput_feedback(tool):
    """Launch USERINPUT interface to collect direct user feedback. Returns user text only."""
    import sys
    if str(tool.project_root) not in sys.path:
        sys.path.insert(0, str(tool.project_root))
    interface_path = tool.project_root / "tool" / "USERINPUT" / "interface" / "main.py"
    if interface_path.exists():
        try:
            from tool.USERINPUT.interface.main import get_user_feedback
            return get_user_feedback(
                hint="GCS: Please provide feedback on the command execution.",
                title="GCS Feedback"
            )
        except Exception:
            pass
    # Fallback: subprocess call
    import subprocess, os
    userinput_bin = tool.project_root / "bin" / "USERINPUT" / "USERINPUT"
    if not userinput_bin.exists():
        userinput_bin = tool.project_root / "bin" / "USERINPUT"
    if not userinput_bin.exists():
        return None
    res = subprocess.run(
        [str(userinput_bin), "--hint", "GCS: Please provide feedback on the command execution."],
        env={**os.environ, "TK_SILENCE_DEPRECATION": "1"},
        capture_output=True, text=True
    )
    return res.stdout.strip() if res.returncode == 0 else None


def _verify_mount_precheck(tool, utils):
    """Quick Drive API check: verify mount fingerprint file exists in REMOTE_ENV/tmp/."""
    import json as _json
    config_path = tool.project_root / "data" / "config.json"
    if not config_path.exists():
        return False
    try:
        with open(config_path, "r") as f:
            cfg = _json.load(f)
    except Exception:
        return False

    mount_hash = cfg.get("mount_hash", "")
    env_id = cfg.get("env_folder_id", "")
    if not mount_hash or not env_id:
        return False

    try:
        ok, items = utils.list_folder_via_api(tool.project_root, env_id, timeout=15)
        if not ok:
            return False
        tmp_folder = next((i for i in items if i.get("name") == "tmp" and i.get("type") == "folder"), None)
        if not tmp_folder:
            return False

        ok2, tmp_items = utils.list_folder_via_api(tool.project_root, tmp_folder["id"], timeout=15)
        if not ok2:
            return False

        fingerprint_name = f".gds_mount_fingerprint_{mount_hash}"
        return any(i.get("name") == fingerprint_name for i in tmp_items)
    except Exception:
        return False


def _get_venv_prefix(state_mgr):
    """If a virtual environment is active, return a shell export statement."""
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
        stage.fail_status = _ts(tool, "turing_cancelled", "Cancelled")
        stage.fail_name = ""
        stage.fail_color = "YELLOW"
        stage.error_brief = _ts(tool, "turing_cancelled_by_user", "Cancelled by user.")
    elif status == "timeout":
        stage.error_brief = _ts(tool, "turing_gui_timed_out", "GUI timed out.")
    elif reason == "drive_not_mounted":
        stage.fail_status = _ts(tool, "turing_failed_to_execute", "Failed to execute")
        stage.fail_name = _ts(tool, "turing_command", "command")
        stage.error_brief = _ts(tool, "turing_drive_not_mounted",
                                "Google Drive not mounted. Run 'GCS --remount' first.")
    elif reason == "mount_fingerprint_invalid":
        stage.fail_status = _ts(tool, "turing_failed_to_execute", "Failed to execute")
        stage.fail_name = _ts(tool, "turing_command", "command")
        stage.error_brief = _ts(tool, "turing_mount_fingerprint_invalid",
                                "Mount fingerprint mismatch. Run 'GCS --remount' to refresh.")
    elif reason == "execution_timeout":
        stage.error_brief = _ts(tool, "turing_execution_timed_out",
                                "Remote execution timed out.")
    elif reason == "colab_tab_not_found":
        stage.error_brief = _ts(tool, "turing_colab_tab_not_found",
                                "Colab notebook tab not found. Run 'GCS --mcp boot' first.")
    elif reason == "cdp_connection_error":
        stage.error_brief = _ts(tool, "turing_cdp_connection_error",
                                "CDP connection failed. Check Chrome is running with remote debugging.")
    elif reason and reason.startswith("cdp_"):
        stage.error_brief = _ts(tool, "turing_cdp_execution_failed",
                                "CDP execution failed.")
    else:
        stage.error_brief = res.get("message",
                                    _ts(tool, "turing_gui_closed_unexpectedly",
                                        "GUI closed unexpectedly."))


def _ts(tool, key, default, **kwargs):
    """Translation helper that tolerates a None tool."""
    if tool is None:
        return default.format(**kwargs) if kwargs else default
    return _t(tool, key, default, **kwargs)
