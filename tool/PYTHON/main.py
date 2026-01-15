#!/usr/bin/env python3
import sys
import subprocess
import os
import json
import argparse
import shutil
import re
from pathlib import Path

# Use resolve() to get the actual location of the script
script_dir = Path(__file__).resolve().parent
# project_root is two levels up: tool/PYTHON -> tool -> root
project_root = script_dir.parent.parent

# Add the directory containing 'proj' to sys.path
sys.path.append(str(script_dir))
from proj.utils import get_python_exec

# Try to import colors and shared utils from root proj
sys.path.append(str(project_root))
try:
    from proj.config import get_color
    from proj.language_utils import get_translation
except ImportError:
    def get_color(name, default="\033[0m"): return default
    def get_translation(d, k, default): return default

# Root shared proj for translations
SHARED_PROJ_DIR = project_root / "proj"

def _(translation_key, default, **kwargs):
    # Try tool-specific translations first
    text = get_translation(str(script_dir), translation_key, None)
    if text is None:
        # Fallback to root translations
        text = get_translation(str(SHARED_PROJ_DIR), translation_key, default)
    return text.format(**kwargs)

# Define commonly used colors with defaults
RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", RESET)
BOLD = get_color("BOLD", RESET)
BLUE = get_color("BLUE", RESET)
YELLOW = get_color("YELLOW", RESET)
RED = get_color("RED", RESET)

def get_config():
    config_path = script_dir / "tool.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def main():
    config = get_config()
    supported_versions = config.get("supported_versions", [])
    default_version = config.get("default_version", "python3.10.19")

    parser = argparse.ArgumentParser(description="PYTHON Proxy and Manager", add_help=False)
    parser.add_argument("--py-version", help="Specify Python version to use")
    parser.add_argument("--py-list", action="store_true", help="List supported and installed versions")
    parser.add_argument("--py-install", help="Install a specific Python version")
    parser.add_argument("--py-dir", help="Specify installation directory")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")

    # Shorthand version detection: if the first unknown argument starts with @3.x, use it as version
    raw_args = sys.argv[1:]
    shorthand_version = None
    remaining_raw_args = []
    
    # Simple manual check for @3.x shorthand to allow it to be at any position 
    # but usually it's the first one.
    filtered_args = []
    from proj.utils import get_system_tag
    tag = get_system_tag()
    install_root = script_dir / "proj" / "install"

    for arg in raw_args:
        if arg.startswith("@3."):
            # Expand shorthand to latest patch version in the branch
            v_minor = arg[1:] # e.g. "3.8"
            
            # Find all matching versions in install_root
            pattern = f"python{v_minor}."
            
            def version_key(v_str):
                # Extract numbers from "python3.8.10" -> [3, 8, 10]
                return [int(x) for x in re.findall(r"\d+", v_str)]

            matching_dirs = [d.name.split("-")[0] for d in install_root.iterdir() 
                            if d.is_dir() and d.name.startswith(pattern)]
            
            if matching_dirs:
                # Sort numerically
                matching_dirs.sort(key=version_key, reverse=True)
                shorthand_version = matching_dirs[0]
            else:
                # Fallback to direct match attempt for others
                shorthand_version = f"python{v_minor}"
        else:
            filtered_args.append(arg)

    # We want to pass all other arguments to the underlying python
    args, unknown = parser.parse_known_args(filtered_args)

    if args.help:
        parser.print_help()
        print(_("python_shorthand_hint", "\nShorthand: Use @3.x (e.g., @3.7) to specify version quickly."))
        print(_("python_pass_args_hint", "All other arguments will be passed to the selected Python executable."))
        return

    if args.py_list:
        _list_versions(supported_versions)
        return

    if args.py_install:
        success = _install_version(args.py_install, args.py_dir)
        sys.exit(0 if success else 1)

    # Determine which python to use:
    # 1. Command line --py-version
    # 2. Shorthand @3.x
    # 3. Environment variable PY_VERSION
    # 4. Default version from tool.json
    selected_version = args.py_version or shorthand_version or os.environ.get("PY_VERSION") or default_version
    python_exec = get_python_exec(selected_version)
    
    if not os.path.exists(python_exec) and python_exec != "python3":
        # Fallback to system python if specified version is not found
        python_exec = "python3"

    # Set up environment for the subprocess
    env = os.environ.copy()
    
    # If we are using a standalone python, set PYTHONHOME to avoid warnings
    # and ensure it finds its own libraries.
    # python_exec is .../proj/install/{version}/install/bin/python3
    if "proj/install/" in python_exec:
        exec_path = Path(python_exec)
        # For Unix: bin is in install/, for Windows: python.exe is in install/
        if exec_path.name == "python.exe":
            python_home = exec_path.parent
        else:
            python_home = exec_path.parent.parent
        
        env["PYTHONHOME"] = str(python_home)
        
        # Also ensure the standalone bin is in PATH
        current_path = env.get("PATH", "")
        env["PATH"] = f"{python_home}/bin:{current_path}"

    python_path = env.get("PYTHONPATH", "")
    new_paths = f"{project_root}:{script_dir}"
    if python_path:
        env["PYTHONPATH"] = f"{new_paths}:{python_path}"
    else:
        env["PYTHONPATH"] = new_paths

    # Execute
    cmd = [python_exec] + unknown
    try:
        # Use subprocess.run without shell=True to pass arguments safely
        subprocess.run(cmd, env=env)
    except KeyboardInterrupt:
        sys.exit(1)

def _list_versions(supported):
    install_dir = script_dir / "proj" / "install"
    installed = []
    if install_dir.exists():
        installed = [d.name for d in install_dir.iterdir() if d.is_dir()]
    
    print(_("python_supported_versions", "Supported versions:"))
    missing = []
    for v in supported:
        # Check if any installation matches this supported version prefix
        is_installed = any(inst.startswith(v) for inst in installed)
        status = f" ({_('python_status_installed', 'installed')})" if is_installed else ""
        print(f"  - {v}{status}")
        if not is_installed:
            missing.append(v)
    
    if missing:
        print(_("python_install_missing_hint", "\nTo install a missing version: PYTHON --py-install {version}", version=missing[0]))
    
    print(_("python_set_default_hint", "\nTo set the default version for this tool, edit 'tool/PYTHON/tool.json'."))

def _install_version(version, install_dir=None):
    """
    Installs a specific Python version from the 'tool' branch.
    If install_dir is provided, it installs there; otherwise, to default installations dir.
    """
    config = get_config()
    supported = config.get("supported_versions", [])
    if version not in supported:
        error_label = _("label_error", "Error")
        print(f"{RED}{BOLD}{error_label}:{RESET} " + _("python_version_not_supported", "Version {version} is not supported. Supported: {supported}", 
                         version=version, supported=", ".join(supported)))
        return False

    target_parent = Path(install_dir) if install_dir else script_dir / "proj" / "install"
    target_parent.mkdir(parents=True, exist_ok=True)
    target_dir = target_parent / version
    
    if target_dir.exists():
        already_label = _("python_already_installed", "{version} is already installed at {path}", version=version, path=target_dir)
        print(f"{GREEN}{BOLD}{already_label}{RESET}")
        return True

    installing_label = _("label_installing", "Installing")
    print(f"{BLUE}{BOLD}{installing_label} {version}{RESET} " + _("python_installing", "to {path}...", version=version, path=target_dir).replace(f"正在安装 {version} ", "").replace(f"جاري تثبيت {version} ", "").replace(f"Installing {version} ", ""))
    
    try:
        # The path in 'tool' branch is now a directory containing a .tar.zst and PYTHON.json
        source_dir_rel = f"resource/tool/PYTHON/proj/install/{version}"
        full_source_path = project_root / source_dir_rel
        
        import tempfile
        from proj.utils import extract_resource
        
        # 1. Check if resource already exists on disk (Local/Same branch optimization)
        resource_ready = False
        zst_files = []
        if full_source_path.exists() and list(full_source_path.glob("*.tar.zst")):
            print(_("python_using_local_resource", "Using locally available resource for {version}...", version=version))
            resource_ready = True
        
        # 2. If not on disk, try to fetch from git
        if not resource_ready:
            print(_("python_fetching_resource", "Fetching resources for {version} from git...", version=version))
            # Fetch first to ensure origin/tool is up to date
            subprocess.run(["git", "fetch", "origin", "tool"], capture_output=True, cwd=str(project_root))
            
            # Try origin/tool first
            cmd = ["git", "checkout", "origin/tool", "--", source_dir_rel]
            result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            
            if result.returncode != 0:
                # Try local 'tool' branch fallback
                cmd = ["git", "checkout", "tool", "--", source_dir_rel]
                result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            
            if result.returncode == 0 and full_source_path.exists():
                resource_ready = True

        if resource_ready:
            # Find the .tar.zst file
            zst_files = list(full_source_path.glob("*.tar.zst"))
            if not zst_files:
                # If metadata exists but zst is missing, try direct download
                json_path = full_source_path / "PYTHON.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r") as f:
                            meta = json.load(f)
                        release = meta.get("release")
                        asset = meta.get("asset")
                        if release and asset:
                            download_url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{release}/{asset}"
                            print(f"{BLUE}Resource metadata found. Downloading from GitHub...{RESET}")
                            print(f"URL: {download_url}")
                            full_source_path.mkdir(parents=True, exist_ok=True)
                            zst_path = full_source_path / asset
                            subprocess.run(["curl", "-L", download_url, "-o", str(zst_path)], check=True)
                            zst_files = [zst_path]
                    except Exception as e:
                        print(f"{YELLOW}Direct download failed: {e}{RESET}")

        # 3. If still not ready, try calling install.py to fetch/install directly
        if not zst_files:
            print(f"{BLUE}Resource not found in project. Attempting to fetch from GitHub releases...{RESET}")
            install_script = script_dir / "proj" / "install.py"
            if install_script.exists():
                # Extract version and platform from the version tag (e.g. python3.10.19-macos-arm64)
                v_match = re.search(r"python([\d\.]+)-(.*)", version)
                if v_match:
                    v_num = v_match.group(1)
                    v_plat = v_match.group(2)
                    cmd = [sys.executable, str(install_script), "--version", v_num, "--platform", v_plat, "--limit", "1"]
                    print(f"Running: {' '.join(cmd)}")
                    subprocess.run(cmd)
                    
                    # Check if it was installed by the script
                    if (target_parent / version).exists():
                        return True

        if not zst_files:
            error_label = _("label_error", "Error")
            print(f"{RED}{BOLD}{error_label}:{RESET} " + _("python_install_failed", "Failed to obtain resource for {version}.", version=version))
            return False
            
        source_zst = zst_files[0]
        # Perform integrated extraction
        if extract_resource(source_zst, target_dir):
            # Success - Astral builds extract to a 'python' folder
            inner_dir = target_dir / "python"
            if inner_dir.exists():
                for item in inner_dir.iterdir():
                    shutil.move(str(item), str(target_dir / item.name))
                inner_dir.rmdir()
            
            # Wrap in 'install' folder for utils.py consistency
            install_wrapper = target_dir / "install"
            install_wrapper.mkdir(exist_ok=True)
            for item in list(target_dir.iterdir()):
                if item.name != "install":
                    shutil.move(str(item), str(install_wrapper / item.name))

            success_label = _("label_success", "Successfully installed")
            print(f"{GREEN}{BOLD}{success_label} {version}{RESET} " + _("python_install_success", "to {path}", version=version, path=target_dir).replace(f"成功安装 {version} ", "").replace(f"تم تثبيت {version} بنجاح ", "").replace(f"Successfully installed {version} ", ""))
            return True
        
        return False
            
    except Exception as e:
        error_label = _("label_error", "Error")
        print(f"{RED}{BOLD}{error_label}:{RESET} " + _("python_install_failed", "Failed to install {version}: {error}", version=version, error=str(e)))
        return False

if __name__ == "__main__":
    main()
