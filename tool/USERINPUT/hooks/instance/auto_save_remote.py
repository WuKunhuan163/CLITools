"""Hook instance: auto_save_remote

Implements the auto-commit + push-to-remote behavior that fires when
USERINPUT begins collecting input. Extracts the logic previously
embedded directly in USERINPUT main.py.

Event: on_interaction_start
"""
import re
import subprocess


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return "/usr/bin/git"
import time

from logic.hooks.engine import HookInstance


class AutoSaveRemote(HookInstance):
    name = "auto_save_remote"
    description = ("Auto-commit local changes and push to remote before "
                   "waiting for user input (git add/commit/push).")
    event_name = "on_interaction_start"
    enabled_by_default = True

    def execute(self, **kwargs):
        tool = kwargs.get("tool")
        if tool is None:
            return {"skipped": True, "reason": "no tool instance"}

        project_root = tool.project_root
        if not (project_root / ".git").exists():
            return {"skipped": True, "reason": "not a git repo"}

        try:
            from interface import get_interface
            git_iface = get_interface("GIT")
            if git_iface is None:
                return {"skipped": True, "reason": "GIT tool unavailable"}
            git_engine = git_iface.get_git_engine()
            current_branch = git_engine.get_current_branch()
        except Exception as e:
            return {"skipped": True, "reason": str(e)}

        try:
            status = subprocess.check_output(
                [_git_bin(), "status", "--porcelain"],
                text=True, cwd=str(project_root), timeout=10
            ).strip()
        except subprocess.TimeoutExpired:
            status = ""

        if not status:
            return {"skipped": True, "reason": "no changes"}

        tag_file = project_root / "data" / "git" / "tag_counter.txt"
        tag_file.parent.mkdir(parents=True, exist_ok=True)
        curr_tag = 0
        if tag_file.exists():
            try:
                with open(tag_file, 'r') as f:
                    curr_tag = int(f.read().strip())
            except Exception:
                pass
        next_tag = (curr_tag + 1) % 10000
        with open(tag_file, 'w') as f:
            f.write(str(next_tag))
        tag_str = f"#{curr_tag:04d}"

        get_msg = tool.get_translation
        ts = time.strftime("%H:%M:%S")
        commit_msg = get_msg(
            "label_auto_commit_msg",
            "USERINPUT auto-commit {tag} at {ts}",
            tag=tag_str, ts=ts
        )

        # Stage 1: commit
        def do_save(stage=None):
            try:
                lock_file = project_root / ".git" / "index.lock"
                if lock_file.exists():
                    if time.time() - lock_file.stat().st_mtime > 10:
                        try:
                            lock_file.unlink()
                        except Exception:
                            pass
                subprocess.run(
                    [_git_bin(), "add", "."],
                    cwd=str(project_root), capture_output=True, timeout=15
                )
                res = subprocess.run(
                    [_git_bin(), "commit", "-m", commit_msg],
                    cwd=str(project_root), capture_output=True, text=True, timeout=15
                )
                if res.returncode != 0 and stage:
                    stage.error_brief = (
                        res.stderr.strip().splitlines()[-1]
                        if res.stderr.strip() else "Git commit failed"
                    )
                    stage.error_full = (
                        f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                    )
                return res.returncode == 0
            except subprocess.TimeoutExpired:
                if stage:
                    stage.error_brief = get_msg(
                        "msg_commit_timeout", "Commit timed out (15s)"
                    )
                return False

        # Stage 2: history maintenance
        def do_maintenance(stage=None):
            try:
                res = git_engine.maintain_history(base=50, stage=stage)
                if res.get("status") == "success" and stage:
                    msg = res.get("message", "history")
                    clean_msg = re.sub(
                        r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])', '', msg
                    )
                    if "maintained history (" in clean_msg:
                        details = clean_msg.split(
                            "maintained history ("
                        )[-1].rstrip(").")
                        stage.success_name = f"history ({details})"
                return res.get("status") in ["success", "skipped"]
            except Exception as e:
                if stage:
                    stage.error_brief = f"Maint Error: {e}"
                return False

        # Stage 3: push to remote
        def do_backup(stage=None):
            try:
                proc = subprocess.Popen(
                    [_git_bin(), "push", "origin",
                     f"HEAD:{current_branch}", "--force"],
                    cwd=str(project_root),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                try:
                    stdout, stderr = proc.communicate(timeout=30)
                    if proc.returncode != 0:
                        err_line = (
                            stderr.decode(errors="replace").strip()
                            .splitlines()[-1]
                            if stderr else "Unknown error"
                        )
                        if stage:
                            stage.error_brief = (
                                get_msg("label_failed", "Failed")
                                + f": {err_line}"
                            )
                            stage.error_full = (
                                f"STDOUT:\n{stdout.decode(errors='replace')}"
                                f"\n\nSTDERR:\n{stderr.decode(errors='replace')}"
                            )
                    return proc.returncode == 0
                except subprocess.TimeoutExpired:
                    try:
                        proc.stdout.close()
                        proc.stderr.close()
                    except Exception:
                        pass
                    if stage:
                        stage.error_brief = get_msg(
                            "msg_push_timeout", "Push timed out (30s)"
                        )
                    return False
            except Exception:
                if stage:
                    stage.error_brief = get_msg(
                        "msg_push_timeout", "Push timed out (30s)"
                    )
                return False

        from interface.turing import TuringStage

        pm = tool.create_progress_machine([
            TuringStage(
                "save", do_save,
                active_status=get_msg(
                    "label_saving_progress", "Saving progress"),
                active_name="",
                success_status=get_msg(
                    "label_successfully_saved", "Successfully saved"),
                fail_status=get_msg(
                    "label_failed_to_save", "Failed to save"),
                bold_part=get_msg(
                    "label_saving_progress", "Saving progress"),
            ),
            TuringStage(
                "maint", do_maintenance,
                active_status=get_msg(
                    "label_maintaining_history", "Maintaining history"),
                active_name="",
                success_status=get_msg(
                    "label_successfully_maintained",
                    "Successfully maintained"),
                success_name=get_msg("label_history", "history"),
                fail_status=get_msg(
                    "label_failed_to_maintain", "Failed to maintain"),
                fail_name=get_msg("label_history", "history"),
                fail_color="YELLOW",
                bold_part=get_msg(
                    "label_maintaining_history", "Maintaining history"),
            ),
            TuringStage(
                "backup", do_backup,
                active_status=get_msg(
                    "label_backing_up_to_remote", "Backing up to remote"),
                active_name="",
                success_status=get_msg(
                    "label_successfully_backed_up",
                    "Successfully backed up"),
                success_name=get_msg("label_to_remote", "to remote"),
                fail_status=get_msg(
                    "label_failed_to_back_up", "Failed to back up"),
                fail_name=get_msg("label_to_remote", "to remote"),
                fail_color="YELLOW",
                bold_part=get_msg(
                    "label_backing_up_to_remote",
                    "Backing up to remote"),
            ),
        ])
        pm.run(ephemeral=True, final_newline=False, final_msg="")
        return {"ok": True, "tag": tag_str}
