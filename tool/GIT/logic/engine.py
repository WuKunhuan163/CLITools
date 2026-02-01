import subprocess
from typing import List, Dict, Any, Optional

class GitEngine:
    """Encapsulates Git operations and GitHub API interactions."""
    
    def __init__(self, project_root: str):
        self.project_root = project_root

    def run_git(self, args: List[str]) -> str:
        """Run a git command and return output."""
        try:
            res = subprocess.run(["git"] + args, check=True, cwd=self.project_root, capture_output=True, text=True)
            return res.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Git command failed: {e.stderr}")

    def list_remote_files(self, branch: str, path: str = "") -> List[str]:
        """List files in a remote branch using git ls-tree."""
        output = self.run_git(["ls-tree", "-r", f"origin/{branch}", path])
        files = []
        for line in output.splitlines():
            if line:
                parts = line.split()
                if len(parts) >= 4:
                    files.append(parts[3])
        return files

    def list_remote_tags(self) -> List[str]:
        """List all tags from remote."""
        output = self.run_git(["ls-remote", "--tags", "origin"])
        tags = []
        for line in output.splitlines():
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    ref = parts[1]
                    if ref.startswith("refs/tags/"):
                        tag = ref[len("refs/tags/"):]
                        if not tag.endswith("^{}"):
                            tags.append(tag)
        return tags

    def fetch_github_api(self, url: str) -> Dict[str, Any]:
        """Fetch from GitHub API with rate limit handling."""
        import requests
        headers = {}
        # Try to get token from env
        import os
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"
            
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return {"success": True, "data": resp.json()}
            elif resp.status_code == 403:
                return {"success": False, "error": "Rate limit exceeded", "status": 403}
            else:
                return {"success": False, "error": f"API error: {resp.status_code}", "status": resp.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}

