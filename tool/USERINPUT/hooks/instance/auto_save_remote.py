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

from interface.hooks import HookInstance


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
        extra_msg = kwargs.get("auto_commit_message", "")
        if extra_msg and extra_msg.strip():
            commit_msg = f"{commit_msg}\n\n{extra_msg.strip()}"

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
                # Use -A to stage deletions too; LFS files no longer on disk
                # are then untracked, keeping only last-commit LFS objects.
                subprocess.run(
                    [_git_bin(), "add", "-A", "."],
                    cwd=str(project_root), capture_output=True, timeout=15
                )
                # Explicitly untrack LFS files missing from disk (belt-and-suspenders)
                lfs_out = subprocess.run(
                    [_git_bin(), "lfs", "ls-files", "--name-only"],
                    cwd=str(project_root), capture_output=True, text=True, timeout=10
                )
                if lfs_out.returncode == 0 and lfs_out.stdout.strip():
                    root = project_root
                    for path in lfs_out.stdout.strip().splitlines():
                        if path and not (root / path).exists():
                            subprocess.run(
                                [_git_bin(), "rm", "--cached", "--ignore-unmatch", path],
                                cwd=str(project_root), capture_output=True, timeout=5
                            )
                res = subprocess.run(
                    [_git_bin(), "commit", "-m", commit_msg],
                    cwd=str(project_root), capture_output=True, text=True, timeout=15
                )
                if res.returncode != 0 and stage:
                    brief = (
                        res.stderr.strip().splitlines()[-1]
                        if res.stderr.strip() else "Git commit failed"
                    )
                    stage.report_error(
                        brief,
                        f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                    )
                return res.returncode == 0
            except subprocess.TimeoutExpired:
                if stage:
                    stage.report_error(
                        get_msg("msg_commit_timeout",
                                "Commit timed out (15s)"),
                        "git commit timed out after 15s. "
                        "Check for large staged files or index.lock."
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
                    stage.report_error(
                        f"Maint Error: {type(e).__name__}",
                        f"{type(e).__name__}: {e}"
                    )
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
                            full = (
                                f"STDOUT:\n{stdout.decode(errors='replace')}"
                                f"\n\nSTDERR:\n{stderr.decode(errors='replace')}"
                            )
                            stage.report_error(
                                get_msg("label_failed", "Failed")
                                + f": {err_line}",
                                full
                            )
                    return proc.returncode == 0
                except subprocess.TimeoutExpired:
                    try:
                        proc.stdout.close()
                        proc.stderr.close()
                    except Exception:
                        pass
                    if stage:
                        stage.report_error(
                            get_msg("msg_push_timeout",
                                    "Push timed out (30s)"),
                            "git push timed out after 30s. "
                            "Check network connectivity and remote status."
                        )
                    return False
            except Exception as exc:
                if stage:
                    stage.report_error(
                        f"Push error: {type(exc).__name__}",
                        f"{type(exc).__name__}: {exc}"
                    )
                return False

        # Stage 4: LFS garbage collection
        def do_lfs_gc(stage=None):
            try:
                lfs_check = subprocess.run(
                    [_git_bin(), "lfs", "ls-files", "--all"],
                    cwd=str(project_root), capture_output=True,
                    text=True, timeout=10
                )
                if not lfs_check.stdout.strip():
                    return True
                subprocess.run(
                    [_git_bin(), "reflog", "expire", "--expire=now", "--all"],
                    cwd=str(project_root), capture_output=True, timeout=30
                )
                subprocess.run(
                    [_git_bin(), "gc", "--prune=now"],
                    cwd=str(project_root), capture_output=True, timeout=60
                )
                subprocess.run(
                    [_git_bin(), "lfs", "prune"],
                    cwd=str(project_root), capture_output=True, timeout=60
                )
                return True
            except Exception as e:
                if stage:
                    stage.report_error(
                        f"LFS GC: {type(e).__name__}",
                        f"{type(e).__name__}: {e}"
                    )
                return False

        from interface.turing import TuringStage

        _dbg_log = project_root / "tmp" / "userinput_timing.log"
        def _dbg(msg):
            try:
                ts = time.strftime("%H:%M:%S")
                ms = int((time.time() % 1) * 1000)
                with open(_dbg_log, "a") as f:
                    f.write(f"[{ts}.{ms:03d}]   hook: {msg}\n")
            except Exception:
                pass

        _orig_save = do_save
        _orig_maint = do_maintenance
        _orig_backup = do_backup
        _orig_lfs = do_lfs_gc

        def do_save_dbg(stage=None):
            _dbg("stage:save BEGIN")
            r = _orig_save(stage)
            _dbg(f"stage:save END result={r}")
            return r
        def do_maint_dbg(stage=None):
            _dbg("stage:maint BEGIN")
            r = _orig_maint(stage)
            _dbg(f"stage:maint END result={r}")
            return r
        def do_backup_dbg(stage=None):
            _dbg("stage:backup BEGIN")
            r = _orig_backup(stage)
            _dbg(f"stage:backup END result={r}")
            return r
        def do_lfs_gc_dbg(stage=None):
            _dbg("stage:lfs_gc BEGIN")
            r = _orig_lfs(stage)
            _dbg(f"stage:lfs_gc END result={r}")
            return r

        do_save = do_save_dbg
        do_maintenance = do_maint_dbg
        do_backup = do_backup_dbg
        do_lfs_gc = do_lfs_gc_dbg

        _dbg("pm.run BEGIN")
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
                fail_name="",
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
            TuringStage(
                "lfs_gc", do_lfs_gc,
                active_status=get_msg(
                    "label_pruning_lfs", "Pruning LFS objects"),
                active_name="",
                success_status=get_msg(
                    "label_pruned_lfs", "Pruned LFS"),
                success_name=get_msg("label_objects", "objects"),
                fail_status=get_msg(
                    "label_failed_to_prune", "Failed to prune"),
                fail_name="LFS",
                fail_color="YELLOW",
                bold_part=get_msg(
                    "label_pruning_lfs", "Pruning LFS objects"),
            ),
        ])
        pm.run(ephemeral=True, final_newline=False, final_msg="")
        _dbg("pm.run END")
        return {"ok": True, "tag": tag_str}
