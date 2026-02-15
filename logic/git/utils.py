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

def get_subtool_resource_path(tool_dir: Path, project_root: Path) -> Optional[Path]:
    """
    Determines the resource path for a subtool based on namespace rules.
    tool/PARENT/tool/SUBTOOL -> resource/tool/PARENT.SUBTOOL
    """
    try:
        rel_path = tool_dir.relative_to(project_root)
        parts = rel_path.parts
        # parts: ('tool', 'PARENT', 'tool', 'SUBTOOL')
        if len(parts) == 4 and parts[0] == 'tool' and parts[2] == 'tool':
            parent = parts[1]
            subtool = parts[3]
            return project_root / "resource" / "tool" / f"{parent}.{subtool}"
    except ValueError:
        pass
    return None

def mirror_subtools_to_resources(project_root: Path):
    """
    Scans for subtools and mirrors them to the resource directory using namespace rules.
    """
    tool_root = project_root / "tool"
    if not tool_root.exists():
        return

    # print(f"DEBUG: Scanning for subtools in {tool_root}...")
    for parent_dir in tool_root.iterdir():
        if not parent_dir.is_dir():
            continue
        
        subtool_root = parent_dir / "tool"
        if not subtool_root.exists():
            continue
            
        for subtool_dir in subtool_root.iterdir():
            if not subtool_dir.is_dir():
                continue
                
            res_path = get_subtool_resource_path(subtool_dir, project_root)
            if res_path:
                # Mirroring logic: delete old resource and copy new one
                if res_path.exists():
                    shutil.rmtree(res_path)
                res_path.parent.mkdir(parents=True, exist_ok=True)
                
                # We copy everything except data/ and logs/
                def ignore_patterns(path, names):
                    return ['data', 'logs', '__pycache__', '.DS_Store', 'report']
                
                shutil.copytree(subtool_dir, res_path, ignore=ignore_patterns)
                # print(f"DEBUG: Mirrored subtool {subtool_dir.name} to {res_path.name}")

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
    Abstracted logic for dev sync: mirror subtools, commit, and push.
    """
    from logic.git.engine import get_current_branch, push_with_progress
    
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")
    start_branch = get_current_branch(project_root)

    # 1. Mirror subtools
    def mirror_action(stage: TuringStage):
        mirror_subtools_to_resources(project_root)
        return True

    tm.add_stage(TuringStage(
        name="subtools to resources",
        action=mirror_action,
        active_status="Mirroring",
        success_status="Mirrored",
        bold_part="Mirroring"
    ))

    # 2. Auto-commit
    def auto_commit(stage: TuringStage):
        status = subprocess.check_output(["/usr/bin/git", "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            if not run_git(["add", "-A"], project_root, stage): return False
            if not run_git(["commit", "-m", f"Auto-sync changes (including mirrored resources) on {start_branch}"], project_root, stage): return False
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

    # 3. Push if on dev
    if start_branch == "dev":
        def push_action(stage: TuringStage):
            return push_with_progress("origin", "dev", cwd=str(project_root))
        
        tm.add_stage(TuringStage(
            name="dev to origin",
            action=push_action,
            active_status="Pushing",
            success_status="Pushed",
            bold_part="Pushing"
        ))

    return tm.run(ephemeral=quiet, final_msg="" if quiet else None, final_newline=False)

def align_branches_logic(project_root: Path, translation_func: Optional[Callable] = None):
    """
    Abstracted logic for dev -> tool -> main -> test alignment.
    """
    from logic.git.engine import get_current_branch
    from logic.utils import cleanup_project_patterns
    
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    
    # Switch to dev first if needed
    start_branch = get_current_branch(project_root)
    
    # 1. Sync dev (includes mirroring)
    if not sync_dev_logic(project_root, quiet=False, translation_func=_):
        return False

    tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")

    # 2. dev -> tool (preserving resources)
    def align_tool(stage: TuringStage):
        env = os.environ.copy()
        side_index = project_root / ".git" / "index_sync_tool"
        env["GIT_INDEX_FILE"] = str(side_index)
        
        try:
            # 1. Start with dev tree
            res = subprocess.run(["/usr/bin/git", "write-tree"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode != 0:
                stage.report_error("Failed to write tree", res.stderr)
                return False
            tree_sha = res.stdout.strip()
            
            # 2. Merge with origin/tool's resource directory
            subprocess.run(["/usr/bin/git", "read-tree", tree_sha], cwd=str(project_root), env=env, check=True, capture_output=True)
            
            # Fetch origin/tool
            if not run_git(["fetch", "origin", "tool"], project_root, stage): return False
            
            # Get resource tree
            res = subprocess.run(["/usr/bin/git", "ls-tree", "origin/tool", "resource"], cwd=str(project_root), capture_output=True, text=True)
            if res.returncode == 0 and res.stdout:
                # Add resource directory
                subprocess.run(["/usr/bin/git", "read-tree", "--prefix=resource", "origin/tool:resource"], cwd=str(project_root), env=env, check=True, capture_output=True)
            
            new_tree = subprocess.check_output(["/usr/bin/git", "write-tree"], cwd=str(project_root), env=env, text=True).strip()
            
            # 3. Create commit
            res = subprocess.run(["/usr/bin/git", "rev-parse", "tool"], cwd=str(project_root), capture_output=True, text=True)
            parent = res.stdout.strip() if res.returncode == 0 else None
            
            commit_args = ["/usr/bin/git", "commit-tree", new_tree, "-m", "Align 'tool' with 'dev' (preserving resources)"]
            if parent: commit_args.extend(["-p", parent])
            
            commit_sha = subprocess.check_output(commit_args, cwd=str(project_root), env=env, text=True).strip()
            
            # 4. Update ref
            subprocess.run(["/usr/bin/git", "update-ref", "refs/heads/tool", commit_sha], cwd=str(project_root), check=True, capture_output=True)
            
            # 5. Push tool
            return run_git(["push", "origin", "tool", "--force"], project_root, stage)
        except Exception as e:
            stage.report_error("Align tool failed", str(e))
            return False
        finally:
            if side_index.exists(): side_index.unlink()

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
