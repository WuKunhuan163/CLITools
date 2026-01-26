import subprocess
import sys
import os
import re
from pathlib import Path

def run_git_command(args, cwd=None, capture_output=True, text=True, silent=False):
    """Executes a git command and returns the result."""
    try:
        result = subprocess.run(["git"] + args, cwd=cwd, capture_output=capture_output, text=text)
        if result.returncode != 0 and not silent:
            # More friendly error message
            err = result.stderr.strip() if result.stderr else "Unknown error"
            if "pathspec" in err and "did not match any files" in err:
                # Common scenario where file is already gone
                pass 
            else:
                print(f"\033[1;33mGit Info\033[0m: 'git {' '.join(args)}' returned code {result.returncode}. {err}")
        return result
    except Exception as e:
        if not silent:
            print(f"\033[1;31mGit Error\033[0m: Failed to execute 'git {' '.join(args)}'. Error: {e}")
        return None

def get_remote_url(remote="origin", cwd=None):
    """Returns the URL of a specific git remote."""
    result = run_git_command(["remote", "get-url", remote], cwd=cwd)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return None

def push_resource_to_remote(local_path, remote_branch, remote="origin", commit_msg=None, cwd=None):
    """
    Adds, commits, and pushes a local resource path to a specific remote branch.
    This is a simplified version of the logic in update.py.
    """
    if not cwd:
        cwd = str(Path(__file__).resolve().parent.parent)
    
    # 1. Add
    run_git_command(["add", str(local_path)], cwd=cwd)
    
    # 2. Commit
    if not commit_msg:
        commit_msg = f"Update resource at {local_path}"
    run_git_command(["commit", "-m", commit_msg], cwd=cwd)
    
    # 3. Push
    # We use HEAD:remote_branch to push current commit to remote branch
    result = run_git_command(["push", remote, f"HEAD:{remote_branch}"], cwd=cwd)
    return result and result.returncode == 0

def list_remote_files(remote_branch, path_prefix, remote="origin", cwd=None):
    """Lists files in a remote branch matching a path prefix using ls-tree."""
    if not cwd:
        cwd = str(Path(__file__).resolve().parent.parent)
    
    # Ensure remote is fetched
    run_git_command(["fetch", remote, remote_branch], cwd=cwd)
    
    cmd = ["ls-tree", "-r", f"{remote}/{remote_branch}", path_prefix]
    result = run_git_command(cmd, cwd=cwd)
    
    if result and result.returncode == 0:
        return result.stdout.strip().split("\n")
    return []

def get_current_branch(cwd=None):
    """Returns the name of the currently checked out branch."""
    result = run_git_command(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if result and result.returncode == 0:
        return result.stdout.strip()
    return "unknown"

def auto_push_if_needed(remote="origin", branch=None, interval=3, cwd=None):
    """
    Checks local commit count and pushes to remote if the count is a multiple of interval.
    Helps protect work progress during automated development.
    """
    if not branch or branch == "unknown":
        branch = get_current_branch(cwd)
    
    # Get total commit count on current branch
    result = run_git_command(["rev-list", "--count", "HEAD"], cwd=cwd)
    if result and result.returncode == 0:
        try:
            count = int(result.stdout.strip())
            if count > 0 and count % interval == 0:
                # We have unpushed commits and we are at the interval
                # Use refined push with progress
                return push_with_progress(remote, branch, cwd=cwd)
        except (ValueError, TypeError):
            pass
    return False

def push_with_progress(remote="origin", branch=None, cwd=None):
    """Pushes to remote with blue erasable status and bold results."""
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")
    
    if not branch:
        branch = get_current_branch(cwd)
        
    status_msg = f"{BOLD}{BLUE}Pushing{RESET} to {remote}/{branch}..."
    sys.stdout.write(f"\r\033[K{status_msg}")
    sys.stdout.flush()
    
    result = run_git_command(["push", remote, f"HEAD:{branch}"], cwd=cwd, silent=True)
    
    # Clear the status line
    sys.stdout.write("\r\033[K")
    sys.stdout.flush()
    
    # Use localized labels if available (fallback to project root logic)
    project_root = Path(__file__).resolve().parent.parent
    sys.path.append(str(project_root))
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
    _ = lambda k, d: get_translation(str(get_logic_dir(project_root)), k, d)

    if result and result.returncode == 0:
        success_label = _("label_success", "Successfully")
        pushed_msg = _("pushed_to", "pushed to {remote}/{branch}", remote=remote, branch=branch)
        print(f"{BOLD}{GREEN}{success_label}{RESET} {pushed_msg}")
        return True
    else:
        err = result.stderr.strip() if result and result.stderr else "Unknown error"
        error_label = _("label_error", "Error")
        failed_msg = _("failed_to_push", "failed to push to {remote}/{branch}: {error}", remote=remote, branch=branch, error=err)
        print(f"{BOLD}{RED}{error_label}{RESET}: {failed_msg}")
        return False

