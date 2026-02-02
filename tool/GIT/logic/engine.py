import subprocess
import requests
import time
from typing import List, Dict, Any, Optional

class GitEngine:
    def __init__(self):
        pass

    def run_git(self, args: List[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        """Runs a git command and returns the result."""
        return subprocess.run(["/usr/bin/git"] + args, cwd=cwd, capture_output=True, text=True)

    def list_remote_files(self, remote: str, branch: str, path: str = "") -> List[str]:
        """Lists files in a remote branch at a specific path."""
        result = self.run_git(["ls-tree", "-r", "--name-only", f"{remote}/{branch}", path])
        if result.returncode == 0:
            return result.stdout.splitlines()
        return []

    def list_remote_tags(self, remote: str) -> List[str]:
        """Lists tags from a remote."""
        result = self.run_git(["ls-remote", "--tags", remote])
        if result.returncode == 0:
            tags = []
            for line in result.stdout.splitlines():
                if "^{}" not in line: # Skip peeled tags
                    parts = line.split("\t")
                    if len(parts) > 1:
                        tag = parts[1].replace("refs/tags/", "")
                        tags.append(tag)
            return tags
        return []

    def fetch_github_api(self, url: str) -> Dict[str, Any]:
        """Fetches data from GitHub API, handling rate limits."""
        while True:
            response = requests.get(url)
            if response.status_code == 200:
                return {
                    "status": "success",
                    "data": response.json()
                }
            elif response.status_code == 403 and "X-RateLimit-Remaining" in response.headers:
                remaining = int(response.headers["X-RateLimit-Remaining"])
                if remaining == 0:
                    reset_time = int(response.headers["X-RateLimit-Reset"])
                    sleep_time = reset_time - int(time.time()) + 1
                    if sleep_time > 0:
                        # In a real tool, we might want to log this or notify the user
                        time.sleep(sleep_time)
                        continue
            
            return {
                "status": "error",
                "code": response.status_code,
                "message": response.text
            }
