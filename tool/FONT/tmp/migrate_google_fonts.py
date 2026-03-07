#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
import time
import argparse
import requests
from pathlib import Path

# Fix shadowing
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path
project_root = script_dir.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.config import get_color
from logic.turing.display.manager import MultiLineManager
from tool.FONT.logic.engine import FontManager

FONTS_CACHE_PATH = script_dir / "google_fonts_cache.json"

BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
GREEN = get_color("GREEN", "\033[32m")
RESET = get_color("RESET", "\033[0m")

def get_remote_status():
    """Get list of fonts already in resource/tool/FONT/data/install/ on origin/tool."""
    rel_path = "resource/tool/FONT/data/install/"
    cmd = ["/usr/bin/git", "ls-tree", "-d", "--name-only", "origin/tool", rel_path]
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    
    migrated = set()
    if res.returncode == 0:
        for line in res.stdout.splitlines():
            migrated.add(line.replace(rel_path, "").strip("/"))
    return migrated

def fetch_google_fonts_list(force=False, manager=None):
    """Fetch list of all font families from Google Fonts GitHub."""
    if not force and FONTS_CACHE_PATH.exists():
        try:
            with open(FONTS_CACHE_PATH, "r") as f:
                cache = json.load(f)
            if time.time() - cache.get("timestamp", 0) < 7 * 24 * 3600:
                return cache.get("families", [])
        except: pass

    start_time = time.time()
    worker_id = "SCAN"
    label = f"{BOLD}{BLUE}Fetching font families{RESET} from Google Fonts"
    
    if manager:
        manager.update(worker_id, f"{label}...")
        
    families = []
    # Google Fonts GitHub structure: ofl/ is the main directory
    api_url = "https://api.github.com/repos/google/fonts/contents/ofl"
    
    try:
        res = requests.get(api_url)
        if res.status_code == 200:
            items = res.json()
            for item in items:
                if item["type"] == "dir":
                    families.append(item["name"])
        
        # Also check 'apache' and 'ufl' directories just in case
        for dir_name in ["apache", "ufl"]:
            res = requests.get(f"https://api.github.com/repos/google/fonts/contents/{dir_name}")
            if res.status_code == 200:
                items = res.json()
                for item in items:
                    if item["type"] == "dir":
                        families.append(item["name"])
    except Exception as e:
        print(f"Error fetching families: {e}")
        return []

    if manager:
        elapsed = int(time.time() - start_time)
        manager.update(worker_id, f"{label}: {BOLD}{GREEN}Found {len(families)} families{RESET} in {elapsed}s", is_final=True)

    try:
        with open(FONTS_CACHE_PATH, "w") as f:
            json.dump({"families": families, "timestamp": time.time()}, f, indent=2)
    except: pass
    
    return families

def main():
    parser = argparse.ArgumentParser(description="Automated Google Fonts Migration")
    parser.add_argument("--force", action="store_true", help="Force refresh available fonts")
    parser.add_argument("--count", type=int, default=5, help="Number of families to migrate")
    args = parser.parse_args()

    manager = MultiLineManager()
    fm = FontManager(project_root)
    
    # 1. Fetch available fonts
    all_families = fetch_google_fonts_list(force=args.force, manager=manager)
    
    # 2. Get remote status
    migrated = get_remote_status()
    
    # 3. Identify missing
    candidates = []
    for f in all_families:
        norm = fm.normalize_name(f)
        if norm not in migrated:
            candidates.append(f)
            
    if not candidates:
        print(f"\n{BOLD}{GREEN}All Google Fonts are migrated!{RESET}")
        return

    to_migrate = candidates[:args.count]
    print(f"\nFound {BOLD}{len(candidates)}{RESET} missing families. Selected {BOLD}{len(to_migrate)}{RESET} for migration.\n")
    
    for family in to_migrate:
        print(f"Migrating {BOLD}{family}{RESET}...")
        if fm.download_and_deploy_google_font(family):
            # Commit and push for each family to keep git history manageable
            norm = fm.normalize_name(family)
            rel_path = f"resource/tool/FONT/data/install/{norm}"
            subprocess.run(["git", "add", rel_path], cwd=str(project_root))
            subprocess.run(["git", "commit", "-m", f"feat(font): add google font {family}"], cwd=str(project_root))
            
            # The user requested automated pushing in batches
            # We can push after each successful migration or at the end
            # Let's push at the end of the batch for efficiency
            
    # Push all commits to 'tool' branch
    print(f"\nPushing migrated fonts to origin/tool...")
    subprocess.run(["git", "push", "origin", "HEAD:tool"], cwd=str(project_root))
    print(f"{BOLD}{GREEN}Done!{RESET}")

if __name__ == "__main__":
    main()

