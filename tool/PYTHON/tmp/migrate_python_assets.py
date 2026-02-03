#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
import threading
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_TOOL_BIN = PROJECT_ROOT / "bin" / "PYTHON"

def run_command(cmd, capture=True):
    try:
        res = subprocess.run(cmd, capture_output=capture, text=True, cwd=str(PROJECT_ROOT))
        return res.returncode == 0, res.stdout, res.stderr
    except Exception as e:
        return False, "", str(e)

def get_migrated_versions():
    # We use 'PYTHON --py-list' to get installed versions, but we want REMOTE versions.
    # Actually, the 'PYTHON --py-update --list' command (internally) or just looking at the report is better.
    # But for simplicity, let's just parse 'PYTHON --py-list' and assume anything not installed is a candidate?
    # No, we want what's not on the REMOTE branch.
    
    print("Checking remote status...")
    # Fetch latest remote resources
    success, stdout, stderr = run_command([str(PYTHON_TOOL_BIN), "--py-update", "--list", "--simple"])
    if not success:
        print(f"Error fetching versions: {stderr}")
        return []
    
    all_versions = [v.strip() for v in stdout.split(",") if v.strip()]
    
    # Get what's already on remote
    resource_rel = "resource/tool/PYTHON/data/install/"
    success, stdout, stderr = run_command(["/usr/bin/git", "ls-tree", "-r", "--name-only", "origin/tool", resource_rel])
    
    migrated = set()
    if success:
        # Paths are resource/tool/PYTHON/data/install/VERSION/PYTHON.json
        for line in stdout.splitlines():
            match = re.search(r"install/([^/]+)/PYTHON.json", line)
            if match:
                migrated.add(match.group(1))
    
    candidates = [v for v in all_versions if v not in migrated]
    
    # Sort candidates by version (newest first)
    def version_key(v_str):
        v_num = re.search(r"(\d+\.\d+\.\d+)", v_str)
        if v_num:
            return [int(x) for x in v_num.group(1).split(".")]
        return [0, 0, 0]
    
    candidates.sort(key=version_key, reverse=True)
    return candidates

def migrate():
    candidates = get_migrated_versions()
    if not candidates:
        print("Everything is up to date!")
        return
    
    to_migrate = candidates[:5]
    print(f"Found {len(candidates)} unmigrated assets. Migrating the top 5:")
    for v in to_migrate:
        print(f"  - {v}")
    
    # Use the existing tool logic to perform migration
    # We pass the versions comma-separated to --py-update
    versions_str = ",".join(to_migrate)
    
    print("\nStarting migration (this may take a while)...")
    # We run it in the foreground so the user sees the progress
    cmd = [str(PYTHON_TOOL_BIN), "--py-update", "--version", versions_str]
    subprocess.run(cmd, cwd=str(PROJECT_ROOT))

if __name__ == "__main__":
    migrate()

