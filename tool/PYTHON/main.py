#!/usr/bin/env python3
import sys
import subprocess
import os
import json
import argparse
import shutil
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
            # Expand shorthand to latest version in the branch
            v_num = arg[1:]
            if v_num == "3.8":
                if (install_root / f"python3.8.5-{tag}").exists():
                    shorthand_version = "python3.8.5"
                elif (install_root / f"python3.8.3-{tag}").exists():
                    shorthand_version = "python3.8.3"
                else:
                    shorthand_version = "python3.8.2"
            elif v_num == "3.7":
                if (install_root / f"python3.7.9-{tag}").exists():
                    shorthand_version = "python3.7.9"
                elif (install_root / f"python3.7.7-{tag}").exists():
                    shorthand_version = "python3.7.7"
                elif (install_root / f"python3.7.4-{tag}").exists():
                    shorthand_version = "python3.7.4"
                else:
                    shorthand_version = "python3.7.3"
            else:
                # Direct match attempt for others like @3.10
                shorthand_version = f"python{v_num}"
        else:
            filtered_args.append(arg)

    # We want to pass all other arguments to the underlying python
    args, unknown = parser.parse_known_args(filtered_args)

    if args.help:
        parser.print_help()
        print("\nShorthand: Use @3.x (e.g., @3.7) to specify version quickly.")
        print("All other arguments will be passed to the selected Python executable.")
        return

    if args.py_list:
        _list_versions(supported_versions)
        return

    if args.py_install:
        _install_version(args.py_install, args.py_dir)
        return

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
    
    print("Supported versions:")
    missing = []
    for v in supported:
        # Check if any installation matches this supported version prefix
        is_installed = any(inst.startswith(v) for inst in installed)
        status = " (installed)" if is_installed else ""
        print(f"  - {v}{status}")
        if not is_installed:
            missing.append(v)
    
    if missing:
        print(f"\nTo install a missing version: PYTHON --py-install {missing[0]}")
    
    print("\nTo set the default version for this tool, edit 'tool/PYTHON/tool.json'.")

def _install_version(version, install_dir=None):
    """
    Installs a specific Python version from the 'tool' branch.
    If install_dir is provided, it installs there; otherwise, to default installations dir.
    """
    config = get_config()
    supported = config.get("supported_versions", [])
    if version not in supported:
        print(f"{RED}" + _("python_version_not_supported", "Error: Version {version} is not supported. Supported: {supported}", 
                         version=version, supported=", ".join(supported)) + f"{RESET}")
        return False

    target_parent = Path(install_dir) if install_dir else script_dir / "proj" / "install"
    target_parent.mkdir(parents=True, exist_ok=True)
    target_dir = target_parent / version
    
    if target_dir.exists():
        print(f"{YELLOW}" + _("python_already_installed", "{version} is already installed at {path}", version=version, path=target_dir) + f"{RESET}")
        return True

    print(f"{BLUE}" + _("python_installing", "Installing {version} to {path}...", version=version, path=target_dir) + f"{RESET}")
    
    try:
        # The path in 'tool' branch is now in the 'resource' store
        source_path = f"resource/tool/PYTHON/proj/install/{version}"
        
        # Temporary directory for checkout
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # We use git checkout from origin/tool
            cmd = ["git", "checkout", "origin/tool", "--", source_path]
            result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            
            if result.returncode != 0:
                # Try local 'tool' branch fallback
                cmd = ["git", "checkout", "tool", "--", source_path]
                result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))

            if result.returncode == 0:
                # Move from the checked out location to the target location
                # The checkout puts it at project_root/tool/PYTHON/proj/install/<version>
                checkout_dir = project_root / source_path
                if checkout_dir.exists():
                    if install_dir:
                        # If custom dir, move it there
                        shutil.move(str(checkout_dir), str(target_dir))
                    else:
                        # If default dir, move it to 'install' folder
                        shutil.move(str(checkout_dir), str(target_dir))
                    
                    # Validation
                    exe = target_dir / "install" / "bin" / "python3"
                    if exe.exists():
                        res = subprocess.run([str(exe), "--version"], capture_output=True, text=True)
                        if res.returncode == 0:
                            print(f"{GREEN}" + _("python_install_success", "Successfully installed {version} to {path}", version=version, path=target_dir) + f"{RESET}")
                            print(f"Validation: {res.stdout.strip()}")
                            return True
            
            print(f"{RED}" + _("python_install_failed", "Failed to install {version}: {error}", version=version, error=result.stderr.decode()) + f"{RESET}")
            return False
            
    except Exception as e:
        print(f"{RED}" + _("python_install_failed", "Failed to install {version}: {error}", version=version, error=str(e)) + f"{RESET}")
        return False

if __name__ == "__main__":
    main()
