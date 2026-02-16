import os
import re
import json
import subprocess
import argparse
import sys
import shutil
import hashlib
from pathlib import Path
from datetime import datetime

# Import shared utilities for translation and config
try:
    # Add tool's parent directory to prioritize tool-specific logic
    tool_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(tool_root))
    
    # Add project root to sys.path to find root logic modules
    sys.path.append(str(tool_root.parent.parent))
    
    from logic.lang.utils import get_translation
    from logic.config import get_color
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
RELEASE_ASSET_FILE = DATA_DIR / "release_asset.json"
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
    return get_translation(str(PYTHON_TOOL_DIR / "logic"), key, default).format(**kwargs)

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

from tool.PYTHON.logic.scanner import PythonScanner
scanner = PythonScanner()

def get_all_assets_from_cache(tag_filter=None, version_filter=None, platform_filter=None):
    """Reads all assets from release_asset.json and flattens them."""
    return scanner.get_filtered_assets(tag_filter=tag_filter, version_filter=version_filter, platform_filter=platform_filter)

def download_and_verify(asset, target_dir):
    """Downloads an asset to tmp, verifies it, then moves to target_dir using a Turing Machine."""
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.utils import run_with_progress, extract_resource, print_success_status
    
    # Use consistent naming: X.Y.Z-platform (no 'python' prefix)
    v_tag = f"{asset['version']}-{asset['platform']}"
    unique_str = f"{asset['tag']}-{asset['name']}"
    dir_hash = hashlib.md5(unique_str.encode()).hexdigest()[:8]
    tmp_dir = TMP_INSTALL_DIR / f"{v_tag}_{dir_hash}"
    
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)
    
    zst_path = tmp_dir / asset["name"]
    extract_dir = tmp_dir / "extract"
    
    def download_action(stage=None):
        prefix = f"{BOLD}{BLUE}Installing{RESET} {v_tag} from GitHub"
        curl_cmd = ["curl", "-L", asset["url"], "-o", str(zst_path)]
        success, err = run_with_progress(curl_cmd, prefix)
        if not success:
            if stage: stage.report_error("Download Error", err)
            return False
        return True

    def extract_action(stage=None):
        if stage: stage.active_name = f"{asset['name']}"
        extract_dir.mkdir(exist_ok=True)
        # Clear logic from sys.modules to avoid collision
        for m in list(sys.modules.keys()):
            if m.startswith("logic.") or m == "logic": del sys.modules[m]
        
        if not extract_resource(zst_path, extract_dir, silent=True):
            if stage: stage.report_error("Extraction Error", f"Failed to extract {asset['name']}")
            return False
        return True

    def verify_action(stage=None):
        # Astral builds extract to a 'python' folder, sometimes with an inner 'install' folder
        py_home = extract_dir / "python"
        if not py_home.exists(): py_home = extract_dir
        if (py_home / "install").exists(): py_home = py_home / "install"
            
        py_bin = py_home / "bin" / "python3" if sys.platform != "win32" else py_home / "python.exe"
        
        try:
            res = subprocess.run([str(py_bin), "--version"], capture_output=True, text=True)
            if asset["version"] in res.stdout or asset["version"] in res.stderr:
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
                return True
            else:
                if stage: stage.report_error("Version Mismatch", f"Expected {asset['version']}, got {res.stdout or res.stderr}")
                return False
        except Exception as e:
            if stage: stage.report_error("Verification Error", str(e))
            return False

    tm = ProgressTuringMachine(project_root=PROJECT_ROOT, tool_name="PYTHON")
    tm.add_stage(TuringStage("download", download_action, active_status="Installing", active_name=f"{v_tag} from GitHub", success_status="Successfully downloaded", success_name=f"{v_tag} from GitHub", success_color="BOLD"))
    tm.add_stage(TuringStage("extract", extract_action, active_status="Extracting", active_name="Python package", success_status="Successfully extracted", success_name="Python package", success_color="BOLD"))
    tm.add_stage(TuringStage("verify", verify_action, active_status="Verifying", active_name="installation", success_status="Successfully verified", success_name="installation", success_color="BOLD"))
    
    try:
        if tm.run(ephemeral=True, final_newline=False):
            print_success_status(f"downloaded {asset['name']}")
            return True
    finally:
        if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Target a specific tag")
    parser.add_argument("--force", action="store_true", help="Ignore cache and force scan")
    parser.add_argument("--limit", type=int, default=3, help="Max assets to download")
    parser.add_argument("--version", help="Download a specific version (e.g. 3.10.19)")
    parser.add_argument("--platform", help="Filter by platform")
    args = parser.parse_args()

    # Use the unified cache with filters applied directly
    filtered = get_all_assets_from_cache(tag_filter=args.tag, version_filter=args.version, platform_filter=args.platform)
    if not filtered:
        print(f"{BOLD}{YELLOW}{_('label_warning', 'Warning')}{RESET}: No matching assets found.")
        return

    # Deduplicate: latest tag and latest patch for each platform/minor
    to_download = []
    seen = set()
    
    # Priority for variants: prefer pgo+lto-full > install_only > full > others
    def variant_priority(name):
        if "pgo+lto-full" in name: return 0
        if "pgo-full" in name: return 1
        if "install_only" in name: return 2
        if "full" in name and "debug" not in name and "noopt" not in name: return 3
        return 10

    # Sort by tag (descending) then patch (descending) then priority
    filtered = sorted(filtered, key=lambda x: (x["tag"], x["patch"], -variant_priority(x["name"])), reverse=True)
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
