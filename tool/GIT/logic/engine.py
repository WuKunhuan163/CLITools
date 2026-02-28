import subprocess
import requests
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

class GitEngine:
    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root

    def get_current_branch(self) -> str:
        """Returns the name of the current branch."""
        res = self.run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(self.project_root) if self.project_root else None)
        return res.stdout.strip() if res.returncode == 0 else ""

    def get_dev_branch(self) -> Optional[str]:
        """Reads the designated development branch from config."""
        if not self.project_root: return None
        config_path = self.project_root / "data" / "config.json"
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    return json.load(f).get("git_dev_branch")
            except: pass
        return None

    def set_dev_branch(self, branch: str):
        """Sets the designated development branch in config."""
        if not self.project_root: return
        data_dir = self.project_root / "data"
        data_dir.mkdir(exist_ok=True)
        config_path = data_dir / "config.json"
        config = {}
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r') as f:
                    config = json.load(f)
            except: pass
        config["git_dev_branch"] = branch
        import json
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

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

    def maintain_history(self, base: int = 50, stage=None) -> Dict[str, Any]:
        """Runs auto_squash_if_needed and returns a structured result dict."""
        from logic.git.engine import auto_squash_if_needed, DEFAULT_SQUASH_CONFIG
        
        config = dict(DEFAULT_SQUASH_CONFIG)
        config["base"] = base
        
        cwd = str(self.project_root) if self.project_root else None
        
        try:
            result = auto_squash_if_needed(cwd=cwd, config=config)
            if result:
                count_res = self.run_git(["rev-list", "--count", "HEAD"], cwd=cwd)
                count = count_res.stdout.strip() if count_res.returncode == 0 else "?"
                return {"status": "success", "message": f"maintained history ({count} commits)"}
            return {"status": "skipped", "message": "No squashing needed"}
        except Exception as e:
            if stage:
                stage.error_brief = str(e)
            return {"status": "error", "message": str(e)}

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
