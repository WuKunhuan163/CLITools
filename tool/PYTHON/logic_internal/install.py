import os
import re
import json
import subprocess
import argparse
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Import shared utilities for translation and config
try:
    # Add tool's parent directory to prioritize tool-specific proj
    tool_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(tool_root))
    
    # Add project root to sys.path to find root proj modules
    sys.path.append(str(tool_root.parent.parent))
    
    from core.lang.utils import get_translation
    from core.config import get_color
    from .config import DATA_DIR, RESOURCE_ROOT, INSTALL_DIR, TMP_INSTALL_DIR, PROJECT_ROOT
except ImportError:
    def get_translation(dir, key, default): return default
    def get_color(name, default="\033[0m"): return default
    PROJECT_ROOT = Path("/Applications/AITerminalTools")
    PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"
    DATA_DIR = PYTHON_TOOL_DIR / "data"
    RESOURCE_ROOT = PROJECT_ROOT / "resource" / "tool" / "PYTHON" / "data" / "install"
    INSTALL_DIR = DATA_DIR / "install"
    TMP_INSTALL_DIR = PROJECT_ROOT / "tmp" / "install"

# Configuration
PROJECT_OWNER = "astral-sh"
PROJECT_NAME = "python-build-standalone"
PROJECT_URL = f"https://github.com/{PROJECT_OWNER}/{PROJECT_NAME}"
REPO_URL = f"{PROJECT_URL}.git"

PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"
CACHE_FILE = DATA_DIR / "release_cache.json"
TAGS_CACHE_FILE = DATA_DIR / "tags_cache.json"
# RESOURCE_ROOT, INSTALL_DIR, TMP_INSTALL_DIR are already imported/defined

# Ensure directories exist
RESOURCE_ROOT.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
TMP_INSTALL_DIR.mkdir(parents=True, exist_ok=True)

# ANSI Colors from core config
RED = get_color("RED", "\033[31m")
GREEN = get_color("GREEN", "\033[32m")
YELLOW = get_color("YELLOW", "\033[33m")
BLUE = get_color("BLUE", "\033[34m")
BOLD = get_color("BOLD", "\033[1m")
RESET = get_color("RESET", "\033[0m")

def resolve_platform(asset_name):
    """Maps an asset name to a canonical platform tag used by the tool."""
    mappings = {
        "macos-arm64": ["aarch64-apple-darwin", "macos-aarch64", "macos-arm64"],
        "macos": ["x86_64-apple-darwin", "macos-x86_64", "macosx", "macos"],
        "linux64-musl": ["x86_64-unknown-linux-musl", "linux-musl"],
        "linux64": ["x86_64-unknown-linux-gnu", "linux64", "linux-x86_64"],
        "windows-amd64": ["x86_64-pc-windows-msvc", "windows-x86_64", "win64"],
        "windows-x86": ["i686-pc-windows-msvc", "windows-i686", "win32"],
        "windows-arm64": ["aarch64-pc-windows-msvc", "windows-aarch64"],
    }
    if "linux-musl" in asset_name or "unknown-linux-musl" in asset_name:
        return "linux64-musl"
    for platform, keys in mappings.items():
        if any(key in asset_name for key in keys):
            return platform
    return None

def _(key, default, **kwargs):
    return get_translation(str(PYTHON_TOOL_DIR / "proj"), key, default).format(**kwargs)

def load_json(path):
    if path.exists():
        try:
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

def print_cache_warning():
    warning_label = _("label_warning", "Warning")
    warning_msg = _("label_warning_cache", "Using cached data. To force update, clear cache.")
    print(f"{BOLD}{YELLOW}{warning_label}{RESET}: {warning_msg}", flush=True)

def get_release_tags(use_cache=True):
    if use_cache and TAGS_CACHE_FILE.exists():
        cache = load_json(TAGS_CACHE_FILE)
        if "tags" in cache and (datetime.now() - datetime.fromisoformat(cache["timestamp"])).days < 1:
            return cache["tags"]

    fetch_msg = _("python_fetching_releases", "Fetching releases from GitHub project {owner} ({url})...", 
                  owner=PROJECT_OWNER, url=PROJECT_URL)
    print(fetch_msg)
    
    cmd = ["git", "ls-remote", "--tags", REPO_URL]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{BOLD}{RED}{_('label_error', 'Error')}{RESET}: Failed to fetch tags.")
        sys.exit(1)
    tags = []
    for line in result.stdout.strip().split("\n"):
        match = re.search(r"refs/tags/(\d{8}(?:T\d+)?)$", line)
        if match: tags.append(match.group(1))
    
    tags = sorted(list(set(tags))) # Ascending (Oldest first)
    save_json(TAGS_CACHE_FILE, {"tags": tags, "timestamp": datetime.now().isoformat()})
    return tags

def fetch_assets_for_tag(tag, use_cache=True):
    cache = load_json(CACHE_FILE)
    if use_cache and tag in cache:
        return cache[tag]["assets"]

    fetch_msg = _("python_fetching_assets", "Fetching assets for the release {tag}...", tag=tag)
    print(fetch_msg, end="\r", flush=True)

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
        minor_v = ".".join(full_v.split(".")[:2])
        patch_str = full_v.split(".")[2]
        try: patch = int(patch_str)
        except ValueError: patch = 0
        
        platform = resolve_platform(name)
        if platform:
            assets.append({
                "name": name,
                "url": f"{PROJECT_URL}/releases/download/{tag}/{name}",
                "version": full_v,
                "minor": minor_v,
                "patch": patch,
                "platform": platform,
                "tag": tag
            })
            
    print("\r" + " " * (len(fetch_msg) + 10) + "\r", end="", flush=True)
    found_msg = _("python_found_assets", "Found {count} unique compatible assets in the release {tag}.", 
                  count=len(assets), tag=tag)
    print(found_msg, flush=True)
    
    cache[tag] = {"assets": assets, "timestamp": datetime.now().isoformat()}
    save_json(CACHE_FILE, cache)
    return assets

import hashlib

def download_and_verify(asset, target_dir):
    """Downloads an asset to tmp, verifies it, then moves to target_dir."""
    v_tag = f"python{asset['version']}-{asset['platform']}"
    
    # Create a unique hash for the temporary directory to avoid conflicts
    unique_str = f"{asset['tag']}-{asset['name']}"
    dir_hash = hashlib.md5(unique_str.encode()).hexdigest()[:8]
    tmp_dir = TMP_INSTALL_DIR / f"{v_tag}_{dir_hash}"
    
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    
    try:
        zst_path = tmp_dir / asset["name"]
        downloading_label = _("label_downloading", "Downloading")
        print(f"{BOLD}{BLUE}{downloading_label}{RESET} {asset['name']}...")
        
        subprocess.run(["curl", "-L", asset["url"], "-o", str(zst_path)], check=True)
        
        # Verify extraction and version
        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir()
        
        # Clear existing proj modules to avoid conflicts with root proj
        if 'proj.utils' in sys.modules: del sys.modules['proj.utils']
        if 'proj' in sys.modules: del sys.modules['proj']
        
        from core.utils import extract_resource
        if not extract_resource(zst_path, extract_dir):
            print(f"{RED}Extraction failed for {asset['name']}{RESET}")
            return False
            
        # Astral builds extract to a 'python' folder, sometimes with an inner 'install' folder
        py_home = extract_dir / "python"
        if not py_home.exists():
            py_home = extract_dir # Fallback
        
        # Check for inner 'install' folder (common in newer Astral builds)
        if (py_home / "install").exists():
            py_home = py_home / "install"
            
        py_bin = py_home / "bin" / "python3" if sys.platform != "win32" else py_home / "python.exe"
        
        res = subprocess.run([str(py_bin), "--version"], capture_output=True, text=True)
        if asset["version"] in res.stdout or asset["version"] in res.stderr:
            print(f"{GREEN}Verification successful: {res.stdout.strip() or res.stderr.strip()}{RESET}")
            
            # Move to final location
            final_dest = target_dir / v_tag
            if final_dest.exists(): shutil.rmtree(final_dest)
            
            # Re-wrap in 'install' folder for consistency
            final_install = final_dest / "install"
            final_install.mkdir(parents=True)
            for item in list(py_home.iterdir()):
                shutil.move(str(item), str(final_install / item.name))
            
            # Write metadata
            save_json(final_dest / "PYTHON.json", {
                "release": asset["tag"],
                "asset": asset["name"],
                "version": asset["version"],
                "platform": asset["platform"]
            })
            
            print(f"{BOLD}{GREEN}{_('label_downloaded', 'Downloaded')}{RESET} {asset['name']}")
            return True
        else:
            print(f"{RED}Version mismatch: expected {asset['version']}, got {res.stdout or res.stderr}{RESET}")
    except Exception as e:
        print(f"{RED}Verification failed: {e}{RESET}")
    finally:
        # Cleanup temporary directory
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
            
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Target a specific tag")
    parser.add_argument("--force", action="store_true", help="Ignore cache and force scan")
    parser.add_argument("--limit", type=int, default=3, help="Max assets to download")
    parser.add_argument("--version", help="Download a specific version (e.g. 3.10.19)")
    parser.add_argument("--platform", help="Filter by platform")
    args = parser.parse_args()

    tags = get_release_tags(use_cache=not args.force)
    if not tags: return

    target_tag = args.tag or tags[-1]
    all_assets = fetch_assets_for_tag(target_tag, use_cache=not args.force)

    # Filter
    filtered = all_assets
    if args.version:
        filtered = [a for a in filtered if a["version"] == args.version or a["version"].startswith(args.version)]
    if args.platform:
        filtered = [a for a in filtered if a["platform"] == args.platform]

    if not filtered:
        # Search all releases if version specified but not found in latest
        if args.version:
            print(f"Version {args.version} not found in {target_tag}, searching all releases...")
            for t in reversed(tags):
                assets = fetch_assets_for_tag(t, use_cache=not args.force)
                filtered = [a for a in assets if a["version"] == args.version]
                if filtered:
                    target_tag = t
                    break
        
    if not filtered:
        print(f"{BOLD}{YELLOW}{_('label_warning', 'Warning')}{RESET}: No matching assets found.")
        return

    # Deduplicate: latest patch for each platform/minor
    to_download = []
    seen = set()
    
    # Priority for variants: prefer pgo+lto-full > install_only > full > others
    def variant_priority(name):
        if "pgo+lto-full" in name: return 0
        if "pgo-full" in name: return 1
        if "install_only" in name: return 2
        if "full" in name and "debug" not in name and "noopt" not in name: return 3
        return 10

    filtered = sorted(filtered, key=lambda x: (x["patch"], -variant_priority(x["name"])), reverse=True)
    for a in filtered:
        key = (a["minor"], a["platform"])
        if key not in seen:
            to_download.append(a)
            seen.add(key)

    download_list = to_download[:args.limit]
    for a in download_list:
        download_and_verify(a, INSTALL_DIR)

if __name__ == "__main__":
    main()
