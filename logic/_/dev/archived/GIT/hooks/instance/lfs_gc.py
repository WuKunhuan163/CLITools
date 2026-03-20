"""Hook instance: lfs_gc

Garbage-collects Git LFS objects after push to keep storage under the
GitHub 10 GB quota.  The strategy:

1. Expire reflog so old commit refs are dropped.
2. Run ``git gc --prune=now`` to remove unreachable objects.
3. Run ``git lfs prune`` to remove locally-unreferenced LFS objects.
4. After force-push, orphaned LFS objects on GitHub are eventually
   GC'd by GitHub's backend.

Combined with the existing history squashing (maintain_history) and
force push, this keeps the number of referenced LFS generations to
a minimum.  The ``stealth=True`` Turing stage ensures this runs
silently unless it fails.
"""
import subprocess
from pathlib import Path

from interface.hooks import HookInstance


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return "/usr/bin/git"


def run_lfs_gc(project_root):
    """Run LFS garbage collection.  Can be called standalone or from hook."""
    root = Path(project_root)
    git = _git_bin()

    lfs_check = subprocess.run(
        [git, "lfs", "ls-files", "--all"],
        cwd=str(root), capture_output=True, text=True, timeout=15
    )
    if not lfs_check.stdout.strip():
        return {"skipped": True, "reason": "no LFS objects"}

    total_before = len(lfs_check.stdout.strip().splitlines())

    subprocess.run(
        [git, "reflog", "expire", "--expire=now", "--all"],
        cwd=str(root), capture_output=True, timeout=30
    )
    subprocess.run(
        [git, "gc", "--prune=now"],
        cwd=str(root), capture_output=True, timeout=60
    )
    result = subprocess.run(
        [git, "lfs", "prune"],
        cwd=str(root), capture_output=True, text=True, timeout=60
    )

    lfs_after = subprocess.run(
        [git, "lfs", "ls-files", "--all"],
        cwd=str(root), capture_output=True, text=True, timeout=15
    )
    total_after = len(lfs_after.stdout.strip().splitlines()) if lfs_after.stdout.strip() else 0

    return {
        "ok": True,
        "lfs_before": total_before,
        "lfs_after": total_after,
        "pruned": total_before - total_after,
        "prune_output": result.stdout.strip()[:500],
    }


class LfsGarbageCollect(HookInstance):
    name = "lfs_gc"
    description = (
        "Prune unreferenced Git LFS objects after push to stay "
        "within the GitHub 10 GB storage quota."
    )
    event_name = "on_post_push"
    enabled_by_default = True

    def execute(self, **kwargs):
        project_root = kwargs.get("project_root")
        if project_root is None:
            return {"skipped": True, "reason": "no project_root"}
        return run_lfs_gc(project_root)
