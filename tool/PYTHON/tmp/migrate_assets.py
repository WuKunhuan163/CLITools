#!/usr/bin/env python3
import os
import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Setup paths
PROJECT_ROOT = Path("/Applications/AITerminalTools")
PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"
RESOURCE_ROOT = PROJECT_ROOT / "resource" / "tool" / "PYTHON" / "data" / "install"
CACHE_DIR = PYTHON_TOOL_DIR / "data"

PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
PROJECT_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}"
REPO_URL = f"{PROJECT_URL}.git"

PLATFORMS = ["macos-arm64", "macos", "linux64", "linux64-musl", "windows-amd64"]

def resolve_platform(asset_name):
    mappings = {
        "macos-arm64": ["aarch64-apple-darwin", "macos-aarch64", "macos-arm64"],
        "macos": ["x86_64-apple-darwin", "macos-x86_64", "macosx", "macos"],
        "linux64-musl": ["x86_64-unknown-linux-musl", "linux-musl"],
        "linux64": ["x86_64-unknown-linux-gnu", "linux64", "linux-x86_64"],
        "windows-amd64": ["x86_64-pc-windows-msvc", "windows-x86_64", "win64"]
    }
    if "linux-musl" in asset_name or "unknown-linux-musl" in asset_name:
        return "linux64-musl"
    for platform, keys in mappings.items():
        if any(key in asset_name for key in keys):
            return platform
    return None

def get_release_tags():
    print(f"Fetching tags from {REPO_URL}...")
    cmd = ["/usr/bin/git", "ls-remote", "--tags", REPO_URL]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: Failed to fetch tags.")
        return []
    tags = []
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    return sorted(list(set(tags)), reverse=True)

def fetch_assets(tag):
    print(f"Fetching assets for {tag}...")
    url = f"{PROJECT_URL}/releases/expanded_assets/{tag}"
    cmd = ["curl", "-L", "-s", "-H", "User-Agent: Mozilla/5.0", url]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    assets = []
    matches = re.findall(r'cpython-([\w\+\-\.]+)\.tar\.zst', result.stdout)
    for name_core in set(matches):
        name = f"cpython-{name_core}.tar.zst"
        v_match = re.search(r"(\d+\.\d+\.\d+)", name)
        if not v_match: continue
        
        full_v = v_match.group(1)
        platform = resolve_platform(name)
        if platform:
            assets.append({
                "name": name,
                "url": f"{PROJECT_URL}/releases/download/{tag}/{name}",
                "version": full_v,
                "platform": platform,
                "tag": tag
            })
    return assets

def migrate():
    RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
    tags = get_release_tags()
    
    migrated_count = 0
    max_migration = 5
    
    for tag in tags:
        if migrated_count >= max_migration:
            break
            
        assets = fetch_assets(tag)
        # Prioritize newer versions
        assets.sort(key=lambda x: [int(c) for c in x["version"].split(".")], reverse=True)
        
        for asset in assets:
            if migrated_count >= max_migration:
                break
                
            dest_dir = RESOURCE_ROOT / f"{asset['version']}-{asset['platform']}"
            if dest_dir.exists():
                # Check if it has the required files
                if (dest_dir / "PYTHON.json").exists() and (dest_dir / asset['name']).exists():
                    continue
            
            print(f"Migrating {asset['version']} for {asset['platform']} (Release {tag})...")
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            zst_path = dest_dir / asset["name"]
            try:
                subprocess.run(["curl", "-L", asset["url"], "-o", str(zst_path)], check=True)
                
                with open(dest_dir / "PYTHON.json", "w") as f:
                    json.dump({
                        "release": asset["tag"],
                        "asset": asset["name"],
                        "version": asset["version"],
                        "platform": asset["platform"],
                        "migrated_at": datetime.now().isoformat()
                    }, f, indent=2)
                
                print(f"Successfully migrated to {dest_dir}")
                migrated_count += 1
            except Exception as e:
                print(f"Failed to migrate {asset['name']}: {e}")
                if dest_dir.exists():
                    shutil.rmtree(dest_dir)

    print(f"Migration finished. Migrated {migrated_count} assets.")

if __name__ == "__main__":
    migrate()


