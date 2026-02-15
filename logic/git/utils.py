import os
import sys
import subprocess
import shutil
import json
from pathlib import Path
from typing import List, Optional, Callable
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage
from logic.config import get_color

def run_git(args, project_root: Path, stage: Optional[TuringStage] = None):
    """Helper to run git commands quietly and capture output."""
    try:
        res = subprocess.run(["/usr/bin/git"] + args, check=True, cwd=str(project_root), capture_output=True, text=True)
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
        status = subprocess.check_output(["/usr/bin/git", "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            if not run_git(["add", "-A"], project_root, stage): return False
            if not run_git(["commit", "-m", f"Auto-sync changes on {start_branch}"], project_root, stage): return False
        return True

    tm.add_stage(TuringStage(
        name=_("on_branch", "local changes on '{branch}'", branch=start_branch),
        action=auto_commit,
        active_status=_("label_committing", "Committing"),
        success_status="Successfully committed",
        success_color="BOLD",
        fail_status="Failed to commit",
        bold_part="Committing"
    ))

    if not tm.run(ephemeral=quiet, final_msg="" if quiet else None, final_newline=False):
        return False

    # Push if on dev (direct call, no Turing stage to avoid redundant line)
    if start_branch == "dev":
        from logic.git.engine import push_with_progress
        if not push_with_progress("origin", "dev", cwd=str(project_root), silent_success=False):
            return False

    return True

def align_branches_logic(project_root: Path, translation_func: Optional[Callable] = None):
    """
    Abstracted logic for dev -> tool -> main -> test alignment.
    """
    from logic.git.engine import get_current_branch
    
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    start_branch = get_current_branch(project_root)
    
    # 1. Sync dev
    if not sync_dev_logic(project_root, quiet=False, translation_func=_):
        return False

    tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")

    # 2. dev -> tool
    def align_tool(stage: TuringStage):
        try:
            if not run_git(["checkout", "tool"], project_root, stage): return False
            if not run_git(["reset", "--hard", "dev"], project_root, stage): return False
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
            res = subprocess.run(["/usr/bin/git", "rev-parse", "tool^{tree}"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode != 0: return False
            tool_tree = res.stdout.strip()
            subprocess.run(["/usr/bin/git", "read-tree", tool_tree], cwd=str(project_root), env=env, check=True, capture_output=True)
            
            restricted = ["tool", "resource", "data", "tmp", "bin"]
            for folder in restricted:
                subprocess.run(["/usr/bin/git", "rm", "-rf", "--cached", "--ignore-unmatch", folder], cwd=str(project_root), env=env, capture_output=True)
            
            new_tree = subprocess.check_output(["/usr/bin/git", "write-tree"], cwd=str(project_root), env=env, text=True).strip()
            
            res = subprocess.run(["/usr/bin/git", "rev-parse", "main"], cwd=str(project_root), capture_output=True, text=True)
            parent = res.stdout.strip() if res.returncode == 0 else None
            
            commit_args = ["/usr/bin/git", "commit-tree", new_tree, "-m", "Align 'main' with 'tool' (framework only)"]
            if parent: commit_args.extend(["-p", parent])
            
            commit_sha = subprocess.check_output(commit_args, cwd=str(project_root), env=env, text=True).strip()
            subprocess.run(["/usr/bin/git", "update-ref", "refs/heads/main", commit_sha], cwd=str(project_root), check=True, capture_output=True)
            
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
            res = subprocess.run(["/usr/bin/git", "rev-parse", "tool"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode != 0: return False
            tool_sha = res.stdout.strip()
            subprocess.run(["/usr/bin/git", "update-ref", "refs/heads/test", tool_sha], cwd=str(project_root), check=True, capture_output=True)
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

    success = tm.run(ephemeral=False, final_newline=False)
    
    # Return to starting branch
    subprocess.run(["/usr/bin/git", "checkout", "-f", start_branch], cwd=str(project_root), capture_output=True)
    
    return success
