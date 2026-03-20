"""Lazy-fetch binary resources from the remote tool branch.

The tool branch is NOT tracked locally. These functions do shallow fetches,
check out requested paths, and clean up tracking refs.
"""
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return "git"


def fetch_resource(tool_name: str, project_root, subpath: str = None) -> Optional[Path]:
    """Lazy-fetch binary resources from the remote tool branch.

    Args:
        tool_name: Name of the tool (e.g. "PYTHON").
        project_root: Path to the project root.
        subpath: Optional subpath within the resource dir.
    Returns:
        Path to the fetched resource directory, or None on failure.
    """
    project_root = Path(project_root)

    resource_rel = f"logic/_/dev/resource/{tool_name}"
    if subpath:
        resource_rel = f"{resource_rel}/{subpath}"

    resource_dir = project_root / resource_rel
    if resource_dir.exists():
        return resource_dir

    try:
        subprocess.run(
            [_git_bin(), "fetch", "origin", "tool", "--depth=1"],
            cwd=str(project_root), capture_output=True
        )

        for ref in ("FETCH_HEAD", "origin/tool"):
            res = subprocess.run(
                [_git_bin(), "checkout", ref, "--", resource_rel],
                cwd=str(project_root), capture_output=True, text=True
            )
            if res.returncode == 0 and resource_dir.exists():
                break
        else:
            old_rel = f"resource/tool/{tool_name}"
            if subpath:
                old_rel = f"{old_rel}/{subpath}"
            for ref in ("FETCH_HEAD", "origin/tool"):
                res = subprocess.run(
                    [_git_bin(), "checkout", ref, "--", old_rel],
                    cwd=str(project_root), capture_output=True, text=True
                )
                old_dir = project_root / old_rel
                if res.returncode == 0 and old_dir.exists():
                    resource_dir.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(str(old_dir), str(resource_dir), dirs_exist_ok=True)
                    shutil.rmtree(project_root / "resource", ignore_errors=True)
                    break

        subprocess.run(
            [_git_bin(), "update-ref", "-d", "refs/remotes/origin/tool"],
            cwd=str(project_root), capture_output=True
        )

        return resource_dir if resource_dir.exists() else None
    except Exception:
        return None
