#!/usr/bin/env python3
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

# Configuration for GitHub scanning
PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
REPO_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}.git"

PYTHON_BIN = project_root / "bin" / "PYTHON"
ASSETS_CACHE_PATH = script_dir / "assets_cache.json"

BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
RESET = get_color("RESET", "\033[0m")

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

def fetch_assets_info(force=False, manager=None):
    """
    Fetch all available assets from GitHub with caching and dynamic UI.
    UI format: Fetching releases from GitHub (aaa) (found: bbb)(xxs)...
    """
    if not force and ASSETS_CACHE_PATH.exists():
        try:
            with open(ASSETS_CACHE_PATH, "r") as f:
                cache = json.load(f)
            # Cache valid for 24 hours
            if time.time() - cache.get("timestamp", 0) < 24 * 3600:
                return cache.get("versions", [])
        except: pass

    # Start scanning logic
    start_time = time.time()
    
    # 1. Fetch tags
    cmd = ["/usr/bin/git", "ls-remote", "--tags", REPO_URL]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        return []
    
    tags = []
    for line in res.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    tags = sorted(list(set(tags)), reverse=True) # Newest first

    # 2. Fetch assets per tag
    all_v_tags = set()
    found_count = 0
    
    worker_id = "SCAN"
    for i, tag in enumerate(tags):
        elapsed = int(time.time() - start_time)
        status = f"{BOLD}{BLUE}Fetching releases from GitHub{RESET} ({tag}) (found: {found_count})({elapsed}s)..."
        if manager:
            manager.update(worker_id, status)
        
        # Use internal tool logic via subprocess to fetch assets for this tag (it's cached internally too)
        # Note: we use --list --simple but for a SINGLE tag
        cmd = [str(PYTHON_BIN), "--py-update", "--list", "--simple", "--tag", tag]
        res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
        
        if res.returncode == 0:
            tag_versions = [v.strip() for v in res.stdout.split(",") if v.strip()]
            for v in tag_versions:
                if v not in all_v_tags:
                    all_v_tags.add(v)
                    found_count += 1
        
        # Update UI frequently
        if manager:
            elapsed = int(time.time() - start_time)
            status = f"{BOLD}{BLUE}Fetching releases from GitHub{RESET} ({tag}) (found: {found_count})({elapsed}s)..."
            manager.update(worker_id, status)

    versions = sorted(list(all_v_tags))
    
    # Finalize UI
    if manager:
        elapsed = int(time.time() - start_time)
        manager.update(worker_id, f"{BOLD}{BLUE}Successfully fetched {len(versions)} versions{RESET} in {elapsed}s", is_final=True)
    
    # Save cache
    try:
        with open(ASSETS_CACHE_PATH, "w") as f:
            json.dump({"versions": versions, "timestamp": time.time()}, f, indent=2)
    except: pass
    
    return versions

def migrate_batch(versions):
    """Run migration using the Turing Machine UI."""
    if not versions:
        return
    
    cmd = [str(PYTHON_BIN), "--py-update", "--version", ",".join(versions)]
    # Run in foreground to allow it to use its own MultiLineManager
    subprocess.run(cmd, cwd=str(project_root))

def main():
    parser = argparse.ArgumentParser(description="Automated Python Asset Migration")
    parser.add_argument("--force", action="store_true", help="Force refresh available versions")
    parser.add_argument("--count", type=int, default=5, help="Number of assets to migrate")
    args = parser.parse_args()

    manager = MultiLineManager()
    
    # 1. Fetch available versions
    all_versions = fetch_assets_info(force=args.force, manager=manager)
    
    # 2. Get remote status
    migrated = get_remote_status()
    
    # 3. Identify missing
    candidates = [v for v in all_versions if v not in migrated]
    
    # Sort by version (newest first)
    def version_key(v_str):
        v_num = re.search(r"(\d+\.\d+\.\d+)", v_str)
        if v_num:
            return [int(x) for x in v_num.group(1).split(".")]
        return [0, 0, 0]
    candidates.sort(key=version_key, reverse=True)
    
    if not candidates:
        print(f"\n{BOLD}Everything is up to date!{RESET}")
        return

    to_migrate = candidates[:args.count]
    print(f"\nFound {BOLD}{len(candidates)}{RESET} missing assets. Selected top {BOLD}{len(to_migrate)}{RESET} for migration.\n")
    
    migrate_batch(to_migrate)

if __name__ == "__main__":
    main()
