import os
import json
import subprocess
import argparse
import sys
import shutil
import hashlib
from pathlib import Path

# Import shared utilities for translation and config
try:
    # Fix shadowing: Remove script directory from sys.path[0] if present
    tool_logic_dir = Path(__file__).resolve().parent
    python_tool_dir = tool_logic_dir.parent
    project_root = python_tool_dir.parent.parent
    
    # Ensure root project is at index 0 to avoid 'logic' shadowing
    if str(project_root) in sys.path:
        sys.path.remove(str(project_root))
    sys.path.insert(0, str(project_root))
    
    # Tool-specific logic at index 1
    if str(python_tool_dir) in sys.path:
        sys.path.remove(str(python_tool_dir))
    sys.path.insert(1, str(python_tool_dir))
    
    from interface.lang import get_translation
    from interface.config import get_color
    from tool.PYTHON.logic.config import DATA_DIR, RESOURCE_ROOT, INSTALL_DIR, TMP_INSTALL_DIR, PROJECT_ROOT
except ImportError:
    def get_translation(dir, key, default): return default
    def get_color(name, default="\033[0m"): return default
    # Dynamically resolve project root as fallback
    _curr = Path(__file__).resolve().parent
    PROJECT_ROOT = _curr.parent.parent.parent
    PYTHON_TOOL_DIR = PROJECT_ROOT / "tool" / "PYTHON"
    DATA_DIR = PYTHON_TOOL_DIR / "data"
    RESOURCE_ROOT = PROJECT_ROOT / "logic" / "_" / "install" / "resource" / "PYTHON" / "data" / "install"
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
    
    for platform, terms in mappings.items():
        if any(t in asset_name for t in terms):
            return platform
    return "unknown"

def _(key, default, **kwargs):
    return get_translation(str(PYTHON_TOOL_DIR / "logic"), key, default).format(**kwargs)

def print_erasable(msg):
    sys.stdout.write(f"\r\033[K{msg}")
    sys.stdout.flush()

def load_json(path):
    if path.exists():
        try:
            with open(path, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(path, data):
    with open(path, "w") as f: json.dump(data, f, indent=2)

from tool.PYTHON.logic.scanner import PythonScanner
scanner = PythonScanner()

def get_all_assets_from_cache(tag_filter=None, version_filter=None, platform_filter=None):
    """Reads all assets from release_asset.json and flattens them."""
    return scanner.get_filtered_assets(tag_filter=tag_filter, version_filter=version_filter, platform_filter=platform_filter)

def download_and_verify(asset, target_root, silent=False):
    """Downloads an asset to tmp, verifies it, then moves to target_dir using a Turing Machine."""
    from interface.turing import ProgressTuringMachine
    from interface.turing import TuringStage
    from interface.utils import run_with_progress, extract_resource, print_success_status
    
    # Use consistent naming: X.Y.Z-platform (no 'python' prefix)
    v_tag = f"{asset['version']}-{asset['platform']}"
    unique_str = f"{asset['tag']}-{asset['name']}"
    dir_hash = hashlib.md5(unique_str.encode()).hexdigest()[:8]
    tmp_dir = TMP_INSTALL_DIR / f"{v_tag}_{dir_hash}"
    
    if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    tmp_dir.mkdir(parents=True)

    zst_path = tmp_dir / asset["name"]
    extract_dir = tmp_dir / "extract"
    target_dir = target_root / v_tag
    
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
        
        if not extract_resource(zst_path, extract_dir, silent=True):
            if stage: stage.report_error("Extraction Error", f"Failed to extract {asset['name']}")
            return False
        return True
            
    def verify_action(stage=None):
        py_home = extract_dir / "python"
        if not py_home.exists(): py_home = extract_dir
        if (py_home / "install").exists(): py_home = py_home / "install"

        py_bin = py_home / "bin" / "python3" if sys.platform != "win32" else py_home / "python.exe"

        try:
            res = subprocess.run([str(py_bin), "--version"], capture_output=True, text=True)
            if asset["version"] in res.stdout or asset["version"] in res.stderr:
                if target_dir.exists(): shutil.rmtree(target_dir)
                final_install = target_dir / "install"
                final_install.mkdir(parents=True)
                for item in list(py_home.iterdir()):
                    shutil.move(str(item), str(final_install / item.name))
                save_json(target_dir / "PYTHON.json", {
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
    tm.add_stage(TuringStage("download", download_action, active_status="Installing", active_name=f"{v_tag} from GitHub", success_status="Successfully downloaded", success_name=f"{v_tag} from GitHub", fail_status="Failed to download", fail_name=f"{v_tag} from GitHub", bold_part="Installing"))
    tm.add_stage(TuringStage("extract", extract_action, active_status="Extracting", active_name="Python package", success_status="Successfully extracted", success_name="Python package", fail_status="Failed to extract", fail_name="Python package", bold_part="Extracting"))
    tm.add_stage(TuringStage("verify", verify_action, active_status="Verifying", active_name="installation", success_status="Successfully verified", success_name="installation", fail_status="Failed to verify", fail_name="installation", bold_part="Verifying"))
    
    try:
        # Use ephemeral=True to avoid artifacts, but if silent is set, we can be even more silent
        is_silent = os.environ.get("TOOL_QUIET") == "1" or silent
        if tm.run(ephemeral=True, final_newline=False):
            if not is_silent:
                # Explicitly erase the last line from run_with_progress
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                print_success_status(f"installed {v_tag}")
            return True
    finally:
        if tmp_dir.exists(): shutil.rmtree(tmp_dir)
    return False

def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--py-tag", dest="tag", help="Target a specific tag")
    parser.add_argument("--force", action="store_true", help="Ignore cache and force scan")
    parser.add_argument("--limit", type=int, default=3, help="Max assets to download")
    parser.add_argument("--py-ver", dest="version", help="Download a specific version (e.g. 3.10.19)")
    parser.add_argument("--py-platform", dest="platform", help="Filter by platform")
    parser.add_argument("--tool-quiet", action="store_true", help="Minimize output for tool-to-tool calls")
    args = parser.parse_args()

    # Use the unified cache with filters applied directly
    PythonScanner(silent=args.tool_quiet)
    filtered = get_all_assets_from_cache(tag_filter=args.tag, version_filter=args.version, platform_filter=args.platform)
    if not filtered:
        from interface.status import fmt_warning
        print(fmt_warning("No matching assets found.", indent=0))
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
        download_and_verify(a, INSTALL_DIR, silent=args.tool_quiet)

if __name__ == "__main__":
    main()
