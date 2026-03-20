import subprocess
import sys
from pathlib import Path

def _git_bin():
    from tool.GIT.interface.main import get_system_git
    return get_system_git()


def run_git_command(args, cwd=None, capture_output=True, text=True, silent=False):
    """Executes a git command and returns the result."""
    try:
        result = subprocess.run([_git_bin()] + args, cwd=cwd, capture_output=capture_output, text=text)
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

DEFAULT_SQUASH_CONFIG = {
    "base": 10,
    "levels": [
        {"level": 1, "frequency": 1.0},
        {"level": 2, "frequency": 1.0/2},
        {"level": 6, "frequency": 1.0/6},
        {"level": 24, "frequency": 1.0/24},
        {"level": 120, "frequency": 1.0/120},
    ]
}


def auto_squash_if_needed(cwd=None, config=None):
    """Long-tail commit squashing using git commit-tree (safe, no working-tree changes).
    
    Keeps recent commits intact, progressively compresses older commits based
    on configurable zone/frequency rules. Uses commit-tree to rebuild history
    from existing tree objects — never touches the working tree or index.
    
    Returns True if any squashing was performed."""
    import time as _time
    if config is None:
        config = DEFAULT_SQUASH_CONFIG
    
    branch = None
    backup_ref = None
    
    try:
        branch = get_current_branch(cwd)
        if not branch or branch in ("HEAD", "unknown"):
            return False
        
        base = config["base"]
        levels = config["levels"]
        
        result = run_git_command(["rev-list", "--count", "HEAD"], cwd=cwd, silent=True)
        if not result or result.returncode != 0:
            return False
        total = int(result.stdout.strip())
        
        if total < base * 2:
            return False
        
        if total % base != 0:
            return False
        
        result = run_git_command(
            ["log", "--format=%H %s", "--reverse"],
            cwd=cwd, silent=True
        )
        if not result or result.returncode != 0:
            return False
        
        lines = result.stdout.strip().split("\n")
        commits = []
        for line in lines:
            parts = line.split(" ", 1)
            commits.append({"sha": parts[0], "msg": parts[1] if len(parts) > 1 else ""})
        
        if len(commits) != total:
            return False
        
        newest_first = list(reversed(commits))
        
        keep_set = set()
        prev_boundary = 0
        for lvl_cfg in levels:
            lvl = lvl_cfg["level"]
            freq = lvl_cfg["frequency"]
            boundary = base * lvl
            if boundary > total:
                boundary = total
            
            zone_start = prev_boundary
            zone_end = boundary
            
            if freq >= 1.0:
                for i in range(zone_start, zone_end):
                    keep_set.add(i)
            else:
                zone_size = zone_end - zone_start
                target_count = max(1, int(zone_size * freq))
                if target_count >= zone_size:
                    for i in range(zone_start, zone_end):
                        keep_set.add(i)
                else:
                    step = zone_size / target_count
                    for j in range(target_count):
                        idx = zone_start + int(j * step)
                        keep_set.add(idx)
            
            prev_boundary = boundary
            if boundary >= total:
                break
        
        if prev_boundary < total:
            last_freq = levels[-1]["frequency"] if levels else 1.0
            remaining = total - prev_boundary
            target = max(1, int(remaining * last_freq))
            step = remaining / target
            for j in range(target):
                idx = prev_boundary + int(j * step)
                keep_set.add(idx)
        
        new_count = len(keep_set)
        if new_count >= total:
            return False
        
        removed = total - new_count
        if removed < 2:
            return False
        
        ts = _time.strftime("%Y%m%d_%H%M%S")
        backup_ref = f"refs/backup/pre_squash_{ts}"
        run_git_command(["update-ref", backup_ref, "HEAD"], cwd=cwd, silent=True)
        
        # Build plan: iterate oldest-first, grouping non-kept commits for squashing
        oldest_first_indices = list(range(len(newest_first) - 1, -1, -1))
        
        build_plan = []
        group = []
        for nf_idx in oldest_first_indices:
            commit = newest_first[nf_idx]
            if nf_idx in keep_set:
                if group:
                    build_plan.append({"type": "squash", "commits": list(group)})
                    group = []
                build_plan.append({"type": "keep", "commit": commit})
            else:
                group.append(commit)
        if group:
            build_plan.append({"type": "squash", "commits": list(group)})
        
        # Drop single-commit squash groups: their state is already captured
        # in the adjacent kept commit's tree (trees are cumulative snapshots).
        # Multi-commit groups are kept as real squash operations.
        build_plan = [
            entry for entry in build_plan
            if not (entry["type"] == "squash" and len(entry["commits"]) == 1)
        ]
        
        if len(build_plan) >= total:
            return False
        
        # Rebuild history using commit-tree: safe, no working-tree or index changes.
        # Each commit's tree object already contains the full file state.
        # For squash groups, we use the LAST commit's tree (cumulative state).
        prev_sha = None
        for step_entry in build_plan:
            if step_entry["type"] == "keep":
                tree_res = run_git_command(["rev-parse", step_entry["commit"]["sha"] + "^{tree}"], cwd=cwd, silent=True)
                if not tree_res or tree_res.returncode != 0:
                    return False
                tree_sha = tree_res.stdout.strip()
                msg = step_entry["commit"]["msg"]
            else:
                last_in_group = step_entry["commits"][-1]
                tree_res = run_git_command(["rev-parse", last_in_group["sha"] + "^{tree}"], cwd=cwd, silent=True)
                if not tree_res or tree_res.returncode != 0:
                    return False
                tree_sha = tree_res.stdout.strip()
                msg = f"GIT_MAINTENANCE: Squashed {len(step_entry['commits'])} commits"
            
            ct_args = ["commit-tree", tree_sha, "-m", msg]
            if prev_sha:
                ct_args += ["-p", prev_sha]
            
            ct_res = run_git_command(ct_args, cwd=cwd, silent=True)
            if not ct_res or ct_res.returncode != 0:
                return False
            prev_sha = ct_res.stdout.strip()
        
        if not prev_sha:
            return False
        
        # Verify: final tree must match original HEAD's tree
        orig_tree = run_git_command(["rev-parse", "HEAD^{tree}"], cwd=cwd, silent=True)
        new_tree = run_git_command(["rev-parse", prev_sha + "^{tree}"], cwd=cwd, silent=True)
        if (not orig_tree or not new_tree or
            orig_tree.stdout.strip() != new_tree.stdout.strip()):
            return False
        
        run_git_command(["reset", "--hard", prev_sha], cwd=cwd, silent=True)
        return True
        
    except Exception:
        if backup_ref and branch:
            try:
                run_git_command(["reset", "--hard", backup_ref], cwd=cwd, silent=True)
            except:
                pass
        return False


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

def push_with_progress(remote="origin", branch=None, cwd=None, silent_success=False):
    """Pushes to remote with blue erasable status and bold results."""
    from logic._.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    get_color("GREEN", "\033[32m")
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
    
    if result and result.returncode == 0:
        if not silent_success:
            # Use localized labels if available
            project_root = Path(__file__).resolve().parent.parent
            sys.path.append(str(project_root))
            from logic._.lang.utils import get_translation
            from logic.utils import get_logic_dir, print_success_status
            _ = lambda k, d, **kwargs: get_translation(str(get_logic_dir(project_root)), k, d).format(**kwargs)
            
            pushed_msg = _("pushed_to", "to {remote}/{branch}", remote=remote, branch=branch)
            # Use standard print_success_status for bolding consistency
            label = _("label_pushed", "pushed")
            print_success_status(f"{label} {pushed_msg}")
        return True
    else:
        # Error reporting remains the same
        project_root = Path(__file__).resolve().parent.parent
        sys.path.append(str(project_root))
        from logic._.lang.utils import get_translation
        from logic.utils import get_logic_dir
        _ = lambda k, d, **kwargs: get_translation(str(get_logic_dir(project_root)), k, d).format(**kwargs)
        
        err = result.stderr.strip() if result and result.stderr else "Unknown error"
        error_label = _("label_error", "Error")
        failed_msg = _("failed_to_push", "failed to push to {remote}/{branch}: {error}", remote=remote, branch=branch, error=err)
        print(f"{BOLD}{RED}{error_label}{RESET}: {failed_msg}")
        return False

