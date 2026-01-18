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

