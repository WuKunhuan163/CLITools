"""Cross-tool interface for GITHUB.

Common GitHub operations exposed for other tools:
  - list_release_tags(owner, repo)  — get all release/tag names
  - get_release_assets(owner, repo, tag) — get assets for a release
  - list_repo_contents(owner, repo, path) — list files in a repo directory
  - clone_repo(url, dest, shallow) — shallow or full clone
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from tool.GITHUB.main import GITHUBTool
except ImportError:
    GITHUBTool = None

try:
    from tool.GIT.interface.main import get_system_git
except ImportError:
    def get_system_git():
        return "git"


def get_github_tool():
    """Return an instance of the GITHUB tool, or None if unavailable."""
    if GITHUBTool is None:
        return None
    return GITHUBTool()


def _api_request(url: str, timeout: int = 30) -> Optional[Any]:
    """Make a GitHub API request, returning parsed JSON or None on failure."""
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AITerminalTools/1.0",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def list_release_tags(owner: str, repo: str) -> List[str]:
    """Get release tags from a GitHub repo via git ls-remote.

    Faster than the API and doesn't count against rate limits.
    Returns tags sorted newest-first.
    """
    git = get_system_git()
    repo_url = f"https://github.com/{owner}/{repo}.git"
    result = subprocess.run(
        [git, "ls-remote", "--tags", repo_url],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        return []

    tags = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        ref_match = re.search(r"refs/tags/(.+)$", line)
        if ref_match:
            tag = ref_match.group(1)
            if not tag.endswith("^{}"):
                tags.append(tag)
    return sorted(list(set(tags)), reverse=True)


def get_release_assets(owner: str, repo: str, tag: str) -> List[Dict[str, Any]]:
    """Get assets for a specific release tag via the GitHub API.

    Returns list of dicts with: name, url (browser_download_url), size, content_type.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    data = _api_request(api_url)
    if not data or "assets" not in data:
        return []

    assets = []
    for item in data["assets"]:
        assets.append({
            "name": item["name"],
            "url": item.get("browser_download_url", ""),
            "size": item.get("size", 0),
            "content_type": item.get("content_type", ""),
        })
    return assets


def get_latest_release(owner: str, repo: str) -> Optional[Dict[str, Any]]:
    """Get the latest release info for a repo."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    return _api_request(api_url)


def list_repo_contents(owner: str, repo: str, path: str = "", ref: str = "main") -> List[Dict[str, Any]]:
    """List files/directories in a GitHub repo path via the API.

    Returns list of dicts with: name, path, type ('file'|'dir'), size, download_url.
    """
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"
    data = _api_request(api_url)
    if not data or not isinstance(data, list):
        return []

    items = []
    for item in data:
        items.append({
            "name": item["name"],
            "path": item["path"],
            "type": item["type"],
            "size": item.get("size", 0),
            "download_url": item.get("download_url"),
        })
    return items


def clone_repo(url: str, dest: str, shallow: bool = True, timeout: int = 120) -> bool:
    """Clone a GitHub repository.

    Args:
        url: Repository URL (https or ssh).
        dest: Local destination path.
        shallow: If True, use --depth 1 for faster clone.
        timeout: Max seconds for the clone operation.

    Returns True on success.
    """
    git = get_system_git()
    cmd = [git, "clone"]
    if shallow:
        cmd.extend(["--depth", "1"])
    cmd.extend([url, dest])

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode == 0


def pull_repo(dest: str, timeout: int = 60) -> bool:
    """Pull latest changes in a cloned repo."""
    git = get_system_git()
    result = subprocess.run(
        [git, "pull", "--ff-only"],
        cwd=dest, capture_output=True, text=True, timeout=timeout,
    )
    return result.returncode == 0


def get_repo_info(owner: str, repo: str) -> Optional[Dict[str, Any]]:
    """Get basic repo info (description, stars, language, etc.)."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    return _api_request(api_url)
