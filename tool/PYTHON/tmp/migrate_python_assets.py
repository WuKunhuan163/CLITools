#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
import time
import argparse
from pathlib import Path

# Fix shadowing: Remove script directory from sys.path[0] if present
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path
project_root = script_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.config import get_color
from logic.turing.display.manager import MultiLineManager

PYTHON_BIN = project_root / "bin" / "PYTHON"
ASSETS_CACHE_PATH = script_dir / "assets_cache.json"

BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
GREEN = get_color("GREEN", "\033[32m")
RESET = get_color("RESET", "\033[0m")

# Configuration for GitHub scanning
PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
REPO_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}.git"

def get_remote_status():
    """Get list of versions already on the 'tool' branch."""
    resource_rel = "resource/tool/PYTHON/data/install/"
    cmd = ["/usr/bin/git", "ls-tree", "-r", "--name-only", "origin/tool", resource_rel]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    
    migrated = set()
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            match = re.search(r"install/([^/]+)/PYTHON.json", line)
            if match:
                migrated.add(match.group(1))
    return migrated

def migrate_batch(versions_with_tags):
    """Run migration using the Turing Machine UI."""
    if not versions_with_tags:
        return
    
    # versions_with_tags is a list of (version, tag)
    # We can group them by tag or just pass them as tag:version
    targets = [f"{t}:{v}" for v, t in versions_with_tags]
    
    cmd = [str(PYTHON_BIN), "--py-update", "--version", ",".join(targets)]
    # Run in foreground to allow it to use its own MultiLineManager
    subprocess.run(cmd, cwd=str(project_root))

def main():
    parser = argparse.ArgumentParser(description="Automated Python Asset Migration")
    parser.add_argument("--force", action="store_true", help="Force refresh available versions")
    parser.add_argument("--count", type=int, default=5, help="Number of assets to migrate")
    args = parser.parse_args()

    manager = MultiLineManager()
    
    # 1. Get remote status first
    migrated = get_remote_status()
    
    # 2. Fetch available versions
    # We'll use a local list to keep track of (version, tag) pairs
    candidates = []
    
    # Fetch tags
    cmd = ["/usr/bin/git", "ls-remote", "--tags", REPO_URL]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"{BOLD}{RED}Error{RESET}: Failed to fetch tags.")
        return
    
    tags = []
    for line in res.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    tags = sorted(list(set(tags)), reverse=True) # Newest first

    start_time = time.time()
    worker_id = "SCAN"
    label = f"{BOLD}{BLUE}Scanning releases{RESET} from GitHub"
    
    found_versions = set()
    
    for tag in tags:
        elapsed = int(time.time() - start_time)
        status = f"{label} ({tag}) (new found: {len(candidates)})({elapsed}s)..."
        manager.update(worker_id, status)
        
        # Use internal tool logic via subprocess to fetch assets for this tag
        cmd = [str(PYTHON_BIN), "--py-update", "--list", "--simple", "--tag", tag]
        # We don't want to use --force here if we want to speed up, but user might want it
        if args.force: cmd.append("--force")
        
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
        
        if res.returncode == 0:
            # Clean up output
            clean_lines = []
            for line in res.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("Warning:") or "Full report saved to" in line:
                    continue
                clean_lines.append(line)
            
            raw_output = ",".join(clean_lines)
            tag_versions = [v.strip() for v in raw_output.split(",") if v.strip()]
            
            new_in_tag = False
            for v in tag_versions:
                if v not in found_versions:
                    found_versions.add(v)
                    if v not in migrated:
                        candidates.append((v, tag))
                        new_in_tag = True
            
            if new_in_tag:
                elapsed = int(time.time() - start_time)
                status = f"{label} ({tag}) (new found: {len(candidates)})({elapsed}s)..."
                manager.update(worker_id, status)
        
        if len(candidates) >= args.count:
            break

    elapsed = int(time.time() - start_time)
    manager.update(worker_id, f"{label}: {BOLD}{GREEN}Found {len(candidates)} candidates{RESET} in {elapsed}s", is_final=True)

    if not candidates:
        print(f"\n{BOLD}{GREEN}Everything is up to date!{RESET}")
        return

    to_migrate = candidates[:args.count]
    print(f"\nSelected {BOLD}{len(to_migrate)}{RESET} assets for migration.\n")
    
    migrate_batch(to_migrate)

if __name__ == "__main__":
    main()
