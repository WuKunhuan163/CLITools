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

    def maintain_history(self, base: int = 50, rules: List[Dict[str, Any]] = None):
        """
        Periodically merges early commits to save space based on a frequency model.
        rules: list of {"level": int, "frequency": float}
        """
        if rules is None:
            rules = [
                {"level": 1, "frequency": 1.0},
                {"level": 5, "frequency": 0.5},
                {"level": 20, "frequency": 0.25},
                {"level": 100, "frequency": 0.05},
                {"level": 1000000, "frequency": 0.01} # Approx infinity
            ]
        
        # 1. Get all commits oldest first
        res = self.run_git(["log", "--format=%H", "--reverse"])
        if res.returncode != 0: return
        commits = res.stdout.splitlines()
        total_count = len(commits)
        
        # index 0 is oldest, index total-1 is newest.
        rev_commits = list(reversed(commits)) # index 0 is newest
        
        # 2. Identify groups to squash
        groups_to_squash = [] # list of (start_idx_in_rev, end_idx_in_rev)
        
        current_idx = 0
        sorted_rules = sorted(rules, key=lambda x: x["level"])
        
        prev_level_limit = 0
        for rule in sorted_rules:
            level_limit = int(rule["level"] * base)
            freq = rule["frequency"]
            
            if freq >= 1.0:
                current_idx = min(total_count, level_limit)
                prev_level_limit = level_limit
                continue
            
            # For this range [prev_level_limit, level_limit), group by 1/freq
            group_size = int(1.0 / freq)
            range_end = min(total_count, level_limit)
            
            # Use current_idx to start from where the previous level ended
            for i in range(max(current_idx, prev_level_limit), range_end, group_size):
                g_start = i
                g_end = min(i + group_size, range_end)
                if g_end - g_start > 1:
                    groups_to_squash.append((g_start, g_end))
            
            current_idx = range_end
            prev_level_limit = level_limit
            if current_idx >= total_count: break

        if not groups_to_squash:
            return

        # 3. Perform squashing
        # We must squash from oldest to newest to maintain stable parent hashes for the rest of the chain.
        # But wait, git rebase -i is better for this.
        # We'll generate a sequence script for git rebase -i.
        
        # Groups are in newest-to-oldest index (rev_commits).
        # We need to convert them back to absolute commits.
        
        # Example: rev_commits index 0 is newest. 
        # Group (50, 52) means rev_commits[50] and rev_commits[51] should be squashed.
        # These are older commits.
        
        # Let's map commit hashes to actions
        commit_actions = {c: "pick" for c in commits}
        
        for g_start, g_end in groups_to_squash:
            # rev_commits[g_start...g_end-1] are to be merged.
            # The OLDEST in this group is rev_commits[g_end-1].
            # The NEWEST in this group is rev_commits[g_start].
            
            oldest_hash = rev_commits[g_end - 1]
            commit_actions[oldest_hash] = "pick"
            for j in range(g_start, g_end - 1):
                commit_actions[rev_commits[j]] = "squash"

        # Create the sequence editor script
        import tempfile
        import os
        
        sequence_content = ""
        for c in commits:
            action = commit_actions[c]
            sequence_content += f"{action} {c}\n"
            
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write(sequence_content)
            tmp_seq_path = f.name
            
        # Run rebase
        # We need to rebase from the very first commit.
        # To rebase the root commit, we use --root.
        env = os.environ.copy()
        env["GIT_SEQUENCE_EDITOR"] = f"cat {tmp_seq_path} >"
        # Set a non-interactive editor to automatically accept the squash messages
        # 'true' on unix just exits with 0, which git takes as 'message accepted'
        env["GIT_EDITOR"] = "true"
        
        print(f"Maintaining GIT history: squashing {len(groups_to_squash)} groups of old commits...")
        # Use subprocess.run with env
        res = subprocess.run(["/usr/bin/git", "rebase", "-i", "--root"], env=env, capture_output=True, text=True, cwd=str(self.project_root) if self.project_root else None)
        
        os.unlink(tmp_seq_path)
        
        if res.returncode == 0:
            print(f"Successfully maintained GIT history.")
            # We might need to force-push if there's a remote
            # self.run_git(["push", "--force"]) 
        else:
            print(f"Failed to maintain GIT history: {res.stderr}")
