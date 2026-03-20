import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable
from logic.utils.turing.models.progress import ProgressTuringMachine
from logic.utils.turing.logic import TuringStage

def _git_bin():
    from tool.GIT.interface.main import get_system_git
    return get_system_git()


def run_git(args, project_root: Path, stage: Optional[TuringStage] = None):
    """Helper to run git commands quietly and capture output."""
    try:
        res = subprocess.run([_git_bin()] + args, check=True, cwd=str(project_root), capture_output=True, text=True)
        if stage: stage.set_captured_output(res.stdout + res.stderr)
        return True
    except subprocess.CalledProcessError as e:
        output = (e.stdout or "") + (e.stderr or "")
        if stage:
            stage.set_captured_output(output)
            stage.report_error(f"Git command failed: {' '.join(args)}", output)
        return False

def sync_dev_logic(project_root: Path, quiet=False, translation_func: Optional[Callable] = None):
    """
    Abstracted logic for dev sync: commit and push current branch.
    """
    from logic.git.engine import get_current_branch, push_with_progress
    
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")
    start_branch = get_current_branch(project_root)

    # Auto-commit
    def auto_commit(stage: TuringStage):
        status = subprocess.check_output([_git_bin(), "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            if not run_git(["add", "-A"], project_root, stage): return False
            if not run_git(["commit", "-m", f"Auto-sync changes on {start_branch}"], project_root, stage): return False
        return True

    committing_label = _("label_committing", "Committing")
    on_branch_label = _("on_branch", "local changes on '{branch}'", branch=start_branch)
    
    tm.add_stage(TuringStage(
        name=on_branch_label,
        action=auto_commit,
        active_status=committing_label,
        success_status=_("label_success_committed", "Successfully committed"),
        success_color="BOLD",
        fail_status=_("label_failed_to_commit", "Failed to commit"),
        bold_part=committing_label + " " + on_branch_label.split("'")[0].strip()
    ))

    if not tm.run(ephemeral=quiet, final_msg="" if quiet else None, final_newline=False):
        return False

    # Push if on dev (direct call, no Turing stage to avoid redundant line)
    if start_branch == "dev":
        from logic.git.engine import push_with_progress
        if not push_with_progress("origin", "dev", cwd=str(project_root), silent_success=quiet):
            return False

    return True

def align_branches_logic(project_root: Path, quiet=False, translation_func: Optional[Callable] = None):
    """
    Abstracted logic for dev -> tool -> main -> test alignment.
    """
    from logic.git.engine import get_current_branch
    
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    start_branch = get_current_branch(project_root)
    
    # 1. Sync current branch (commit changes)
    if not sync_dev_logic(project_root, quiet=quiet, translation_func=_):
        return False

    # If we are NOT on dev, merge back to dev first
    if start_branch != "dev":
        tm_merge = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")
        
        def merge_back_action(stage: TuringStage):
            try:
                if not run_git(["checkout", "dev"], project_root, stage): return False
                if not run_git(["merge", start_branch], project_root, stage): return False
                if not run_git(["push", "origin", "dev"], project_root, stage): return False
                return True
            except Exception as e:
                stage.report_error(f"Merge {start_branch} into dev failed", str(e))
                return False

        tm_merge.add_stage(TuringStage(
            name=_("merge_info", "changes on '{branch}' into 'dev'", branch=start_branch),
            action=merge_back_action,
            active_status=_("label_merging", "Merging"),
            success_status=_("label_success_merged", "Successfully merged"),
            success_color="BOLD",
            fail_status=_("label_failed_to_merge", "Failed to merge"),
            bold_part=_("label_merging", "Merging") + " " + _("merge_info", "changes on '{branch}'", branch=start_branch).split("'")[0].strip()
        ))
        
        if not tm_merge.run(ephemeral=quiet, final_msg="" if quiet else None, final_newline=False):
            return False

    tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")

    # 2. dev -> tool (archive all tools, preserve install resources)
    def align_tool(stage: TuringStage):
        try:
            if not run_git(["checkout", "tool"], project_root, stage): return False

            res = subprocess.run([_git_bin(), "rev-parse", "HEAD"],
                                 cwd=str(project_root), capture_output=True, text=True)
            old_tool_sha = res.stdout.strip() if res.returncode == 0 else None

            if not run_git(["reset", "--hard", "dev"], project_root, stage): return False

            # Restore install resources from old tool branch
            if old_tool_sha:
                subprocess.run(
                    [_git_bin(), "checkout", old_tool_sha, "--", "logic/_/install/"],
                    cwd=str(project_root), capture_output=True, text=True
                )
                # Backward compat: old tool branches may still have resource/
                subprocess.run(
                    [_git_bin(), "checkout", old_tool_sha, "--", "resource/"],
                    cwd=str(project_root), capture_output=True, text=True
                )
                old_resource = project_root / "resource"
                if old_resource.exists():
                    new_install = project_root / "logic" / "_" / "install"
                    old_archived = old_resource / "archived"
                    old_tool_res = old_resource / "tool"
                    if old_archived.exists():
                        dest = new_install / "archived"
                        dest.mkdir(parents=True, exist_ok=True)
                        for item in old_archived.iterdir():
                            target = dest / item.name
                            if not target.exists():
                                shutil.copytree(item, target, dirs_exist_ok=True) if item.is_dir() else shutil.copy2(item, target)
                    if old_tool_res.exists():
                        dest = new_install / "resource"
                        dest.mkdir(parents=True, exist_ok=True)
                        for item in old_tool_res.iterdir():
                            target = dest / item.name
                            if not target.exists():
                                shutil.copytree(item, target, dirs_exist_ok=True) if item.is_dir() else shutil.copy2(item, target)
                    shutil.rmtree(old_resource)

            # Archive all tools from tool/ -> logic/_/install/archived/
            tool_dir = project_root / "tool"
            archived_dir = project_root / "logic" / "_" / "install" / "archived"
            if tool_dir.exists():
                archived_dir.mkdir(parents=True, exist_ok=True)
                for td in tool_dir.iterdir():
                    if td.is_dir() and (td / "main.py").exists():
                        dest = archived_dir / td.name
                        if dest.exists():
                            shutil.rmtree(dest)
                        shutil.copytree(td, dest, dirs_exist_ok=True)
                        # Strip data/ from archived copies (untracked, handled by locker)
                        archived_data = dest / "data"
                        if archived_data.exists():
                            shutil.rmtree(archived_data)

                # Remove tool/ directory entirely
                shutil.rmtree(tool_dir)

            # Stage changes and amend
            subprocess.run([_git_bin(), "add", "-A"],
                           cwd=str(project_root), capture_output=True)
            res = subprocess.run([_git_bin(), "diff", "--cached", "--quiet"],
                                 cwd=str(project_root), capture_output=True)
            if res.returncode != 0:
                subprocess.run(
                    [_git_bin(), "commit", "--amend", "--no-edit"],
                    cwd=str(project_root), capture_output=True
                )

            if not run_git(["push", "origin", "tool", "--force"], project_root, stage): return False
            return True
        except Exception as e:
            stage.report_error("Align tool failed", str(e))
            return False

    tm.add_stage(TuringStage(
        name="'tool' from 'dev'",
        action=align_tool,
        active_status="Aligning",
        success_status="Successfully aligned",
        success_color="BOLD",
        fail_status="Failed to align",
        bold_part="Aligning"
    ))

    # 3. tool -> main (framework only)
    def align_main(stage: TuringStage):
        env = os.environ.copy()
        side_index = project_root / ".git" / "index_sync_main"
        env["GIT_INDEX_FILE"] = str(side_index)
        
        try:
            res = subprocess.run([_git_bin(), "rev-parse", "tool^{tree}"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode != 0: return False
            tool_tree = res.stdout.strip()
            subprocess.run([_git_bin(), "read-tree", tool_tree], cwd=str(project_root), env=env, check=True, capture_output=True)
            
            restricted = ["tool", "logic/_/install", "resource", "data", "tmp", "bin"]
            for folder in restricted:
                subprocess.run([_git_bin(), "rm", "-rf", "--cached", "--ignore-unmatch", folder], cwd=str(project_root), env=env, capture_output=True)
            
            new_tree = subprocess.check_output([_git_bin(), "write-tree"], cwd=str(project_root), env=env, text=True).strip()
            
            res = subprocess.run([_git_bin(), "rev-parse", "main"], cwd=str(project_root), capture_output=True, text=True)
            parent = res.stdout.strip() if res.returncode == 0 else None
            
            commit_args = [_git_bin(), "commit-tree", new_tree, "-m", "Align 'main' with 'tool' (framework only)"]
            if parent: commit_args.extend(["-p", parent])
            
            commit_sha = subprocess.check_output(commit_args, cwd=str(project_root), env=env, text=True).strip()
            subprocess.run([_git_bin(), "update-ref", "refs/heads/main", commit_sha], cwd=str(project_root), check=True, capture_output=True)
            
            return run_git(["push", "origin", "main", "--force"], project_root, stage)
        except Exception as e:
            stage.report_error("Align main failed", str(e))
            return False
        finally:
            if side_index.exists(): side_index.unlink()

    tm.add_stage(TuringStage(
        name="'main' from 'tool'",
        action=align_main,
        active_status="Aligning",
        success_status="Successfully aligned",
        success_color="BOLD",
        fail_status="Failed to align",
        bold_part="Aligning"
    ))

    # 4. tool -> test
    def align_test(stage: TuringStage):
        try:
            res = subprocess.run([_git_bin(), "rev-parse", "tool"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode != 0: return False
            tool_sha = res.stdout.strip()
            subprocess.run([_git_bin(), "update-ref", "refs/heads/test", tool_sha], cwd=str(project_root), check=True, capture_output=True)
            return run_git(["push", "origin", "test", "--force"], project_root, stage)
        except Exception as e:
            stage.report_error("Align test failed", str(e))
            return False

    tm.add_stage(TuringStage(
        name="'test' from 'tool'",
        action=align_test,
        active_status="Aligning",
        success_status="Successfully aligned",
        success_color="BOLD",
        fail_status="Failed to align",
        bold_part="Aligning"
    ))

    success = tm.run(ephemeral=quiet, final_msg="" if quiet else None, final_newline=False)
    
    # Return to starting branch
    subprocess.run([_git_bin(), "checkout", "-f", start_branch], cwd=str(project_root), capture_output=True)
    
    return success
