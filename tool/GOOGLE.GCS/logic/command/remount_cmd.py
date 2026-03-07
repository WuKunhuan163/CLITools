#!/usr/bin/env python3
"""GCS --remount command: generate and execute Colab remount script via GUI."""
import sys
from pathlib import Path
from logic.interface.config import get_color
from logic.interface.turing import ProgressTuringMachine
from logic.interface.turing import TuringStage


def execute(tool, args, state_mgr, load_logic, **kwargs):
    remount_mod = load_logic("remount")
    script, metadata = remount_mod.generate_remount_script(tool.project_root)
    if not script:
        print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: {metadata}")
        return 1

    logic_script = Path(__file__).resolve().parent.parent / "remount.py"
    gui_args = [
        "--script-path", "",
        "--ts", metadata["ts"],
        "--hash", metadata["session_hash"],
        "--project-root", str(tool.project_root)
    ]

    def gui_action(stage=None):
        gui_queue_mod = load_logic("command/gui_queue")
        gui_q = gui_queue_mod.get_gui_queue(tool.project_root)

        tmp_script = tool.project_root / "tmp" / f"gcs_remount_{metadata['ts']}.py"
        tmp_script.parent.mkdir(parents=True, exist_ok=True)
        with open(tmp_script, 'w') as f:
            f.write(script)
        gui_args[1] = str(tmp_script)
        old_quiet = getattr(tool, "is_quiet", False)
        tool.is_quiet = True
        try:
            res = gui_q.run_gui_subprocess(
                tool, sys.executable, str(logic_script), 300,
                args=gui_args, request_id=f"remount_{metadata['ts']}"
            )
        finally:
            tool.is_quiet = old_quiet
        if tmp_script.exists():
            tmp_script.unlink()
        if res.get("status") == "success":
            return True
        if stage:
            _set_failure_reason(stage, res)
        return False

    def verify_action(stage=None):
        import time
        time.sleep(1.0)
        ok, msg = remount_mod.verify_local_remount_result(
            tool.project_root, metadata["ts"], metadata["session_hash"], stage=stage
        )
        if not ok and stage:
            stage.fail_status = "Failed to verify"
            stage.fail_name = "remount result"
            stage.error_brief = msg
        return ok

    def _t(key, default):
        try:
            from logic.interface.lang import get_translation
            logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
            return get_translation(logic_dir, key, default)
        except Exception:
            return default

    waiting_label = _t("turing_waiting_user_action", "Waiting for user action")
    verifying_label = _t("turing_verifying_result", "Verifying the remount result file")

    pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GCS", log_dir=tool.get_log_dir())
    pm.add_stage(TuringStage(
        "user action", gui_action,
        active_status="", active_name=waiting_label,
        fail_status="Failed to complete", success_status="Completed",
        success_name="user action", bold_part=waiting_label
    ))
    pm.add_stage(TuringStage(
        "result file", verify_action,
        active_status="", active_name=verifying_label,
        fail_status="Failed to verify", fail_name="remount result",
        success_status="Verified", success_name="remount result",
        bold_part=verifying_label
    ))

    if pm.run(ephemeral=True):
        print(f"{get_color('BOLD')}{get_color('GREEN')}Successfully remounted{get_color('RESET')} Google Drive from Google Colab.")
        import json
        config_path = tool.project_root / "data" / "config.json"
        if config_path.exists():
            with open(config_path, "r") as f:
                cfg = json.load(f)
            cfg["mount_hash"] = metadata["session_hash"]
            with open(config_path, "w") as f:
                json.dump(cfg, f, indent=2)
        return 0
    return 1


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
