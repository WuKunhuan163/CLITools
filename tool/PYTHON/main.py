#!/usr/bin/env python3
import sys
import subprocess
import os
import json
import argparse
import shutil
import re
from pathlib import Path

# Fix shadowing: Remove script directory from sys.path[0] if present
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add root project to sys.path to find root 'logic' and other 'tool' modules
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.utils import get_python_exec, extract_resource
from tool.PYTHON.logic.config import INSTALL_DIR, RESOURCE_ROOT, PROJECT_ROOT, get_rel_install_path, ensure_dirs

# Try to import colors and shared utils from root proj
try:
    from logic.config import get_color
    from logic.lang.utils import get_translation
    from logic.tool.base import ToolBase
except ImportError:
    def get_color(name, default="\033[0m"): return default
    def get_translation(d, k, default): return default
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.script_dir = Path(__file__).resolve().parent
            self.project_root = self.script_dir.parent.parent
        def handle_command_line(self, parser=None):
            if len(sys.argv) > 1 and sys.argv[1] == "setup":
                setup_script = self.script_dir / "setup.py"
                if setup_script.exists():
                    subprocess.run([sys.executable, str(setup_script)] + sys.argv[2:])
                    sys.exit(0)
            return False

# Root shared proj for translation
SHARED_PROJ_DIR = project_root / "logic"

def _(translation_key, default, **kwargs):
    # Try tool-specific translation first (absolute import path)
    text = get_translation(str(script_dir / "logic"), translation_key, None)
    if text is None:
        # Fallback to root translation
        text = get_translation(str(project_root / "logic"), translation_key, default)
    return text.format(**kwargs)

# Define commonly used colors with defaults
RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", RESET)
BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
YELLOW = get_color("YELLOW", "\033[33m")
RED = get_color("RED", "\033[31m")
WHITE = get_color("WHITE", "\033[37m")

def print_erasable(msg):
    # \r: move to start, \033[K: clear from cursor to end
    sys.stdout.write(f"\r\033[K{msg}")
    sys.stdout.flush()

def get_config():
    config_path = script_dir / "tool.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def _get_remote_versions():
    """Fetches the list of versions available in the remote 'tool' branch."""
    versions = []
    rel_path = RESOURCE_ROOT.relative_to(project_root)
    
    # Check origin/tool first
    cmd = ["/usr/bin/git", "ls-tree", "-r", "--name-only", "origin/tool", str(rel_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    
    if result.returncode != 0:
        # Try local tool branch
        cmd = ["/usr/bin/git", "ls-tree", "-r", "--name-only", "tool", str(rel_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    
    if result.returncode == 0:
        # Extract version names from paths: resource/tool/PYTHON/data/install/{version}/PYTHON.json
        pattern = str(rel_path) + "/([^/]+)/"
        for line in result.stdout.splitlines():
            match = re.search(pattern, line)
            if match:
                v = match.group(1)
                if v not in versions:
                    versions.append(v)
    
    return sorted(versions)

def main():
    config = get_config()
    default_version = config.get("default_version", "3.11.14")

    # Initialize parser early so it can be used for help
    parser = argparse.ArgumentParser(description="PYTHON Proxy and Manager", add_help=False, allow_abbrev=False)
    parser.add_argument("--py-version", help="Specify Python version to use")
    parser.add_argument("--py-list", action="store_true", help="List supported and installed versions")
    parser.add_argument("--py-install", help="Install a specific Python version")
    parser.add_argument("--py-uninstall", help="Uninstall a specific Python version (use 'all' for all versions)")
    parser.add_argument("--py-default", help="Set the default Python version for this tool")
    parser.add_argument("--py-update", action="store_true", help="Update Python resources from GitHub releases")
    parser.add_argument("--force", action="store_true", help="Force action (e.g. refresh list cache)")
    parser.add_argument("--py-dir", help="Specify installation directory")
    parser.add_argument("--py-tag", dest="tag", help="Filter by release tag (e.g. 20260211)")
    parser.add_argument("--py-ver", dest="version", help="Filter by version prefix (e.g. 3.12)")
    parser.add_argument("--py-platform", dest="platform", help="Filter by platform")
    parser.add_argument("--limit-releases", type=int, help="Limit number of releases to scan")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")

    # Use ToolBase for common command handling (like setup)
    tool = ToolBase("PYTHON")
    if tool.handle_command_line(parser):
        return

    # Shorthand version detection
    raw_args = sys.argv[1:]
    shorthand_version = None
    filtered_args = []
    
    from logic.utils import get_system_tag
    tag = get_system_tag()
    install_root = INSTALL_DIR

    for arg in raw_args:
        if arg.startswith("@3."):
            v_minor = arg[1:] # e.g. "3.8"
            pattern = f"python{v_minor}."
            if not any(d.is_dir() and d.name.startswith(pattern) for d in install_root.iterdir() if install_root.exists()):
                 # If not in install_root, just use prefix
                 shorthand_version = f"python{v_minor}"
            else:
                def version_key(v_str):
                    return [int(x) for x in re.findall(r"\d+", v_str)]
                matching_dirs = [d.name.split("-")[0] for d in install_root.iterdir() 
                                if d.is_dir() and d.name.startswith(pattern)]
                if matching_dirs:
                    matching_dirs.sort(key=version_key, reverse=True)
                    shorthand_version = matching_dirs[0]
        else:
            filtered_args.append(arg)

    args, unknown = parser.parse_known_args(filtered_args)

    if args.help:
        parser.print_help()
        print(_("python_shorthand_hint", "\nShorthand: Use @3.x (e.g., @3.7) to specify version quickly."))
        print(_("python_pass_args_hint", "All other arguments will be passed to the selected Python executable."))
        return

    RED = get_color("RED")
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    if args.py_list:
        _list_versions(force=args.force, tag_filter=args.tag, version_filter=args.version, platform_filter=args.platform, limit_releases=args.limit_releases)
        return

    if args.py_install:
        success = _install_version(args.py_install, args.py_dir, tag_filter=args.tag, platform_filter=args.platform)
        sys.exit(0 if success else 1)

    if args.py_uninstall:
        _uninstall_version(args.py_uninstall, args.py_dir)
        sys.exit(0)

    if args.py_default:
        _set_default_version(args.py_default)
        sys.exit(0)

    if args.py_update:
        update_script = script_dir / "logic" / "update.py"
        if update_script.exists():
            update_cmd = [sys.executable, str(update_script)]
            if args.tag: update_cmd.extend(["--py-tag", args.tag])
            if args.version: update_cmd.extend(["--py-ver", args.version])
            if args.platform: update_cmd.extend(["--py-platform", args.platform])
            if args.force: update_cmd.append("--force")
            subprocess.run(update_cmd + unknown)
            sys.exit(0)
        else:
            print(f"{RED}Error{RESET}: Update script not found.")
            sys.exit(1)

    if len(unknown) > 0 and unknown[0] == "test":
        # Handle 'PYTHON test'
        test_dir = project_root / "test"
        if test_dir.exists():
            # Run all test_xx_*.py files in the root test/ directory
            test_files = sorted(list(test_dir.glob("test_*.py")))
            if not test_files:
                print(f"{BOLD}{YELLOW}{_('label_warning', 'Warning')}{RESET}: No test files found.")
                sys.exit(0)
                
            for tf in test_files:
                print(f"\n{BOLD}{BLUE}Running test:{RESET} {tf.name}")
                # Use current python_exec if possible, otherwise sys.executable
                subprocess.run([sys.executable, str(tf)])
            sys.exit(0)
        else:
            print(f"{RED}Error{RESET}: Test directory not found.")
            sys.exit(1)

    selected_version = args.py_version or shorthand_version or os.environ.get("PY_VERSION") or default_version
    from tool.PYTHON.logic.utils import get_python_exec as get_py_exec
    python_exec = get_py_exec(selected_version)
    
    if not os.path.exists(python_exec) and python_exec != "python3":
        python_exec = "python3"

    env = os.environ.copy()
    if get_rel_install_path() in python_exec:
        exec_path = Path(python_exec)
        if exec_path.name == "python.exe":
            python_home = exec_path.parent
        else:
            python_home = exec_path.parent.parent
        env["PYTHONHOME"] = str(python_home)
        current_path = env.get("PATH", "")
        env["PATH"] = f"{python_home}/bin:{current_path}"

    python_path = env.get("PYTHONPATH", "")
    new_paths = f"{project_root}:{script_dir}"
    if python_path:
        env["PYTHONPATH"] = f"{new_paths}:{python_path}"
    else:
        env["PYTHONPATH"] = new_paths

    cmd = [python_exec] + unknown
    try:
        res = subprocess.run(cmd, env=env)
        sys.exit(res.returncode)
    except KeyboardInterrupt:
        sys.exit(1)

def _set_default_version(version):
    config = get_config()
    config["default_version"] = version
    config_path = script_dir / "tool.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    success_status = _("python_install_success_status", "Successfully updated")
    print(f"{GREEN}{BOLD}{success_status}{RESET} default version to {version}")

def _uninstall_version(version, install_dir=None):
    install_root = Path(install_dir) if install_dir else INSTALL_DIR
    if version == "all":
        if install_root.exists():
            msg = f"{BLUE}{BOLD}Uninstalling all versions{RESET}..."
            print_erasable(msg)
            for d in install_root.iterdir():
                if d.is_dir():
                    shutil.rmtree(d)
            sys.stdout.write("\r\033[K")
            success_status = _("python_uninstall_success_status", "Successfully uninstalled")
            print(f"{GREEN}{BOLD}{success_status}{RESET} all versions.")
        return

    target_dir = install_root / version
    if target_dir.exists():
        msg = f"{BLUE}{BOLD}Uninstalling{RESET} {version}..."
        print_erasable(msg)
        shutil.rmtree(target_dir)
        sys.stdout.write("\r\033[K")
        success_status = _("python_uninstall_success_status", "Successfully uninstalled")
        print(f"{GREEN}{BOLD}{success_status}{RESET} {version}.")
    else:
        error_label = _("label_error", "Error")
        print(f"{RED}{BOLD}{error_label}{RESET}: Version {version} is not installed.")

def _list_versions(force=False, tag_filter=None, version_filter=None, platform_filter=None, limit_releases=None):
    from tool.PYTHON.logic.config import DATA_DIR, INSTALL_DIR, RESOURCE_ROOT
    from tool.PYTHON.logic.scanner import PythonScanner
    
    installed = []
    if INSTALL_DIR.exists():
        installed = [d.name for d in INSTALL_DIR.iterdir() if d.is_dir()]
    
    scanner = PythonScanner(force=force)
    
    if force or not (DATA_DIR / "release_asset.json").exists():
        scanner.scan_all(limit_releases=limit_releases)
    
    # Apply filters using the new scanner
    assets = scanner.get_filtered_assets(tag_filter=tag_filter, version_filter=version_filter, platform_filter=platform_filter)
    remote_versions = sorted(list(set([a["v_tag"] for a in assets])))
    
    # 2. Get local resources (migrated)
    migrated = []
    if RESOURCE_ROOT.exists():
        for d in RESOURCE_ROOT.iterdir():
            if d.is_dir() and (d / "PYTHON.json").exists():
                migrated.append(d.name)
    
    # 3. Combine and Display
    label = _("python_supported_versions", "Supported versions")
    
    def version_key(v_str):
        # Extract X.Y.Z part
        v_num = re.search(r"(\d+\.\d+\.\d+)", v_str)
        if v_num:
            return [int(x) for x in v_num.group(1).split(".")]
        # Fallback for major.minor
        v_min = re.search(r"(\d+\.\d+)", v_str)
        if v_min:
            return [int(x) for x in v_min.group(1).split(".")] + [0]
        return [0, 0, 0]

    # If any filter is applied, we only show versions that match the filter
    if tag_filter or version_filter or platform_filter:
        all_versions = sorted(list(set(remote_versions)), key=version_key)
    else:
        all_versions = sorted(list(set(remote_versions + installed + migrated)), key=version_key)
    
    if not all_versions:
        print(f"{BOLD}{label}{RESET}:")
        print("  (No versions found matching the criteria.)")
        return

    # Filter for current platform by default for cleaner list if no platform filter specified
    from logic.utils import get_system_tag
    tag = get_system_tag()
    
    display_rows = []
    for v in all_versions:
        # If platform filter is set, we don't need to auto-filter by current platform
        if not platform_filter and tag not in v and "-" in v: continue 
        
        is_installed = v in installed
        is_migrated = v in migrated
        
        status_parts = []
        if is_installed: status_parts.append(_("label_installed", "installed"))
        if is_migrated: status_parts.append(_("label_migrated", "migrated"))
        
        status = f" ({', '.join(status_parts)})" if status_parts else ""
        display_rows.append(f"{v}{status}")
    
    print(f"{BOLD}{label}{RESET}:")
    for row in display_rows:
        print(f"  {row}")
        
    # 4. Save Audit Record
    if display_rows:
        from logic.utils import save_list_report
        report_path = save_list_report(display_rows, save_dir="python_list", filename_prefix="python_versions")
        if report_path:
            print(f"\n{BOLD}{WHITE}Full result saved to{RESET}: {report_path}")

def _install_version(version, install_dir=None, tag_filter=None, platform_filter=None):
    from tool.PYTHON.logic.config import DATA_DIR, INSTALL_DIR, RESOURCE_ROOT
    from tool.PYTHON.logic.scanner import PythonScanner
    
    scanner = PythonScanner()
    
    # Check local cache for all available versions from astral-sh
    cache_path = DATA_DIR / "release_asset.json"
    if not cache_path.exists():
        scanner.scan_all(limit_releases=10)
    
    all_assets = scanner.get_filtered_assets(tag_filter=tag_filter, platform_filter=platform_filter)
    all_available = sorted(list(set([a["v_tag"] for a in all_assets])))
    
    # Compatibility layer: handle 'python' prefix and platform tags
    from logic.utils import get_system_tag
    tag = get_system_tag()
    
    final_version = None
    
    # Try exact match first
    if version in all_available:
        final_version = version
    else:
        # Normalize input
        v = version
        if v.startswith("python"): v = v[6:]
        
        # Try version-tag
        candidate = f"{v}-{tag}"
        if candidate in all_available:
            final_version = candidate
        else:
            # Try fuzzy match
            matches = [s for s in all_available if s.startswith(v) and s.endswith(tag)]
            if matches:
                matches.sort(key=len, reverse=True)
                final_version = matches[0]

    error_label = _("label_error", "Error")
    if not final_version:
        if all_available:
            msg = _("python_version_not_supported", "Version {version} is not found in remote project or local cache.", version=version)
            print(f"{RED}{BOLD}{error_label}{RESET}: {msg}")
            print(_("python_update_hint", "You can use 'PYTHON --py-update --py-ver {v}' to scan and migrate it.", v=version.split('-')[0]))
        else:
            print(f"{RED}{BOLD}{error_label}{RESET}: No versions found. Please run 'PYTHON --py-list' to scan releases.")
        return False

    version = final_version
    target_parent = Path(install_dir) if install_dir else INSTALL_DIR
    target_parent.mkdir(parents=True, exist_ok=True)
    target_dir = target_parent / version
    
    if target_dir.exists():
        already_msg = _("python_already_installed", "{version} is already installed", version=version)
        print(f"{BOLD}{already_msg}{RESET} at {target_dir}")
        return True

    try:
        source_dir_rel = str(RESOURCE_ROOT.relative_to(project_root) / version)
        full_source_path = RESOURCE_ROOT / version
        from logic.utils import extract_resource
        
        resource_ready = False
        zst_files = []
        
        if full_source_path.exists() and list(full_source_path.glob("*.tar.zst")):
            action = _("label_installing", "Installing")
            print_erasable(f"{BLUE}{BOLD}{action}{RESET} {version} from local resource...")
            resource_ready = True
        
        if not resource_ready:
            action = _("label_fetching", "Fetching")
            print_erasable(f"{BLUE}{BOLD}{action}{RESET} {version} from git...")
            subprocess.run(["/usr/bin/git", "fetch", "origin", "tool"], capture_output=True, cwd=str(project_root))
            
            cmd = ["/usr/bin/git", "checkout", "origin/tool", "--", source_dir_rel]
            result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            if result.returncode != 0:
                cmd = ["/usr/bin/git", "checkout", "tool", "--", source_dir_rel]
                result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            
            if result.returncode == 0 and full_source_path.exists():
                resource_ready = True

        if resource_ready:
            zst_files = list(full_source_path.glob("*.tar.zst"))
            if not zst_files:
                json_path = full_source_path / "PYTHON.json"
                if json_path.exists():
                    try:
                        with open(json_path, "r") as f:
                            meta = json.load(f)
                        release = meta.get("release")
                        asset = meta.get("asset")
                        if release and asset:
                            download_url = f"https://github.com/astral-sh/python-build-standalone/releases/download/{release}/{asset}"
                            action = _("label_installing", "Installing")
                            print_erasable(f"{BLUE}{BOLD}{action}{RESET} {version} from GitHub...")
                            full_source_path.mkdir(parents=True, exist_ok=True)
                            zst_path = full_source_path / asset
                            subprocess.run(["curl", "-L", download_url, "-o", str(zst_path)], capture_output=True, check=True)
                            zst_files = [zst_path]
                    except Exception: pass

        if not zst_files:
            action = _("label_installing", "Installing")
            print_erasable(f"{BLUE}{BOLD}{action}{RESET} {version} from GitHub...")
            install_script = script_dir / "logic" / "install.py"
            if install_script.exists():
                # Extract version and platform from 'version' which is 'X.Y.Z-platform'
                parts = version.split("-", 1)
                v_num = parts[0]
                v_plat = parts[1] if len(parts) > 1 else tag
                
                # Use sys.executable to ensure we use the same environment
                cmd = [sys.executable, str(install_script), "--py-ver", v_num, "--py-platform", v_plat, "--limit", "1", "--tool-quiet"]
                # Also pass --py-tag if available
                # Note: args.tag is not available here, we should pass it from main() if needed.
                # For now, install.py will find the latest matching asset.
                
                # DO NOT capture output so the user sees progress
                res = subprocess.run(cmd)
                
                # Check if it was successfully installed
                if (target_parent / version).exists():
                    # Success message already printed by install.py
                    return True
                else:
                    print(f"\n{RED}{BOLD}{error_label}{RESET}: GitHub installation failed for {version}.")
                    return False

        if not zst_files:
            sys.stdout.write("\r\033[K")
            error_label = _("label_error", "Error")
            print(f"{RED}{BOLD}{error_label}{RESET}: " + _("python_install_failed", "Failed to obtain resource for {version}.", version=version))
            return False
            
        source_zst = zst_files[0]
        action = _("label_extracting", "Extracting")
        print_erasable(f"{BLUE}{BOLD}{action}{RESET} {version}...")
        
        if extract_resource(source_zst, target_dir, silent=True):
            inner_dir = target_dir / "python"
            if inner_dir.exists():
                for item in inner_dir.iterdir():
                    shutil.move(str(item), str(target_dir / item.name))
                inner_dir.rmdir()
            install_wrapper = target_dir / "install"
            install_wrapper.mkdir(exist_ok=True)
            for item in list(target_dir.iterdir()):
                if item.name != "install":
                    shutil.move(str(item), str(install_wrapper / item.name))
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            success_status = _("python_install_success_status", "Successfully installed")
            print(f"{GREEN}{BOLD}{success_status}{RESET} {version}")
            return True
        sys.stdout.write("\r\033[K")
        return False
    except Exception as e:
        error_label = _("label_error", "Error")
        print(f"{RED}{BOLD}{error_label}{RESET}: " + _("python_install_failed", "Failed to install {version}: {error}", version=version, error=str(e)))
        return False

if __name__ == "__main__":
    main()
