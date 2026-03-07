#!/usr/bin/env python3
"""GCS remote command execution: send bash/Python commands to Colab via GUI."""
import os
import sys
from pathlib import Path
from logic.interface.config import get_color
from logic.interface.turing import ProgressTuringMachine
from logic.interface.turing import TuringStage


def _t(tool, key, default, **kwargs):
    """Get GCS translated string."""
    try:
        from logic.interface.lang import get_translation
        logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        return default.format(**kwargs) if kwargs else default


def execute(tool, remote_command, state_mgr, load_logic, as_python=False, capture=False, **kwargs):
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
    finished_label = _t(tool, "remote_finished", "Finished")

    cdp_enabled = os.environ.get("GCS_CDP_ENABLED") == "1"
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

    waiting_label = _t(tool, "turing_waiting_user_action", "Waiting for user action")
    verifying_label = _t(tool, "turing_verifying_result", "Verifying the command result file")

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GCS", log_dir=tool.get_log_dir())
    fail_complete_label = _t(tool, "turing_failed_to_complete", "Failed to complete")
    completed_label = _t(tool, "turing_completed_user_action", "Completed")
    user_action_label = _t(tool, "turing_user_action", "user action")
    fail_execute_label = _t(tool, "turing_failed_to_execute", "Failed to execute")
    retrieved_label = _t(tool, "turing_retrieved_result", "Retrieved")
    exec_result_label = _t(tool, "turing_execution_result", "execution result")
    command_label = _t(tool, "turing_command", "command")

    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="", active_name=waiting_label,
        fail_status=fail_complete_label, success_status=completed_label,
        success_name=user_action_label, bold_part=waiting_label
    ))
    pm.add_stage(TuringStage(
        "command execution", verify_action,
        active_status="", active_name=verifying_label,
        fail_status=fail_execute_label, fail_name=command_label,
        success_status=retrieved_label, success_name=exec_result_label,
        bold_part=verifying_label
    ))

    if pm.run(ephemeral=True):
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
    interface_path = tool.project_root / "tool" / "USERINPUT" / "logic" / "interface" / "main.py"
    if interface_path.exists():
        try:
            from tool.USERINPUT.logic.interface.main import get_user_feedback
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


def _set_failure_reason(stage, res):
    status = res.get("status", "error")
    reason = res.get("reason", "")
    if status == "cancelled" or reason in ("interrupted", "signal", "stop"):
        stage.fail_status = "Cancelled"
        stage.fail_name = ""
        stage.fail_color = "YELLOW"
        stage.error_brief = "Cancelled by user."
    elif status == "timeout":
        stage.error_brief = "GUI timed out."
    else:
        stage.error_brief = res.get("message", "GUI closed unexpectedly.")
