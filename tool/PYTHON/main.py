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

# Add root logic to sys.path first to avoid shadowing
sys.path.insert(0, str(project_root))
from logic.utils import extract_resource, get_logic_dir
from logic.config import get_color
from logic.lang.utils import get_translation
from logic.tool.base import ToolBase

# Import tool-specific logic
try:
    from tool.PYTHON.logic.utils import get_python_exec, extract_resource
    from tool.PYTHON.logic.config import INSTALL_DIR, RESOURCE_ROOT, PROJECT_ROOT, get_rel_install_path, ensure_dirs
except ImportError:
    # Fallback using importlib
    import importlib.util
    def load_mod(name, path):
        spec = importlib.util.spec_from_file_location(name, str(path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    
    python_logic_utils = load_mod("python_logic_utils", script_dir / "logic" / "utils.py")
    python_logic_config = load_mod("python_logic_config", script_dir / "logic" / "config.py")
    
    get_python_exec = python_logic_utils.get_python_exec
    extract_resource = python_logic_utils.extract_resource
    INSTALL_DIR = python_logic_config.INSTALL_DIR
    RESOURCE_ROOT = python_logic_config.RESOURCE_ROOT
    PROJECT_ROOT = python_logic_config.PROJECT_ROOT
    get_rel_install_path = python_logic_config.get_rel_install_path
    ensure_dirs = python_logic_config.ensure_dirs

TOOL_INTERNAL = get_logic_dir(script_dir)

def _(translation_key, default, **kwargs):
    # Try tool-specific translation first
    text = get_translation(str(TOOL_INTERNAL), translation_key, None)
    if text is None:
        # Fallback to root translation
        text = get_translation(str(project_root / "logic"), translation_key, default)
    return text.format(**kwargs)

# Define commonly used colors with defaults
RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", RESET)
BOLD = get_color("BOLD", RESET)
BLUE = get_color("BLUE", RESET)
YELLOW = get_color("YELLOW", RESET)
RED = get_color("RED", RESET)

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
    
    # Always fetch latest info
    subprocess.run(["git", "fetch", "origin", "tool"], capture_output=True, cwd=str(project_root))
    
    # Check origin/tool first
    cmd = ["git", "ls-tree", "-r", "--name-only", "origin/tool", str(rel_path)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
    
    if result.returncode != 0:
        # Try local tool branch
        cmd = ["git", "ls-tree", "-r", "--name-only", "tool", str(rel_path)]
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
    # Use ToolBase for common command handling (like setup)
    tool = ToolBase("PYTHON")
    if tool.handle_command_line():
        return

    config = get_config()
    default_version = config.get("default_version", "3.10.19")

    parser = argparse.ArgumentParser(description="PYTHON Proxy and Manager", add_help=False)
    parser.add_argument("--py-version", help="Specify Python version to use")
    parser.add_argument("--py-list", action="store_true", help="List supported and installed versions")
    parser.add_argument("--py-install", help="Install a specific Python version")
    parser.add_argument("--py-uninstall", help="Uninstall a specific Python version (use 'all' for all versions)")
    parser.add_argument("--py-default", help="Set the default Python version for this tool")
    parser.add_argument("--py-update", action="store_true", help="Update Python resources from GitHub releases")
    parser.add_argument("--py-dir", help="Specify installation directory")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")

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

    if args.py_list:
        _list_versions(unknown[0] if unknown else None)
        return

    if args.py_install:
        success = _install_version(args.py_install, args.py_dir)
        sys.exit(0 if success else 1)

    if args.py_uninstall:
        _uninstall_version(args.py_uninstall, args.py_dir)
        sys.exit(0)

    if args.py_default:
        _set_default_version(args.py_default)
        sys.exit(0)

    if args.py_update:
        update_script = TOOL_INTERNAL / "update.py"
        if update_script.exists():
            subprocess.run([sys.executable, str(update_script)] + unknown)
            sys.exit(0)
        else:
            print(f"{RED}{BOLD}Error{RESET}: Update script not found.")
            sys.exit(1)

    selected_version = args.py_version or shorthand_version or os.environ.get("PY_VERSION") or default_version
    python_exec = get_python_exec(selected_version)
    
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
        subprocess.run(cmd, env=env)
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

def _list_versions(filter_str=None):
    installed = []
    if INSTALL_DIR.exists():
        installed = [d.name for d in INSTALL_DIR.iterdir() if d.is_dir()]
    
    remote_versions = _get_remote_versions()
    
    if not remote_versions:
        # Try to migrate at least one version to ensure list is not empty as suggested
        update_script = TOOL_INTERNAL / "update.py"
        if update_script.exists():
            action = _("python_fetching_resource", "Fetching resources...")
            print_erasable(f"{BLUE}{BOLD}{action}{RESET}")
            subprocess.run([sys.executable, str(update_script), "--limit-releases", "1"], capture_output=True)
            sys.stdout.write("\r\033[K")
            remote_versions = _get_remote_versions()

    if not remote_versions:
        label = _("python_supported_versions", "Supported versions")
        print(f"{BOLD}{label}{RESET}:")
        print("  (No versions found on remote 'tool' branch. Use 'PYTHON --py-update' to migrate some.)")
        return

    # Helper for counting and grouping
    def get_count_label(prefix, versions):
        matches = [v for v in versions if v.startswith(prefix)]
        return len(matches), matches

    if not filter_str:
        # Level 1: python<a>.<b> (<count>)
        groups = {}
        for v in remote_versions:
            # v format: X.Y.Z-platform or pythonX.Y.Z-platform
            v_clean = v[6:] if v.startswith("python") else v
            v_match = re.match(r"(\d+\.\d+)", v_clean)
            if v_match:
                minor = v_match.group(1)
                prefix = f"python{minor}"
                if prefix not in groups:
                    groups[prefix] = 0
                groups[prefix] += 1
        
        label = _("python_supported_versions", "Supported versions")
        print(f"{BOLD}{label}{RESET}:")
        for prefix in sorted(groups.keys(), key=lambda x: [int(i) for i in re.findall(r"\d+", x)], reverse=True):
            hint = _("python_list_level1_hint", " (Use {BOLD}PYTHON --py-list {prefix}{RESET} to see specific {count} versions)", 
                     BOLD=BOLD, RESET=RESET, prefix=prefix, count=groups[prefix])
            print(f"  - {prefix} ({groups[prefix]}){hint}")
            
    elif re.match(r"^python\d+\.\d+$", filter_str):
        # Level 2: python<a>.<b>.<c> (<count>)
        prefix = filter_str[6:] # Remove 'python' prefix for matching
        groups = {}
        for v in remote_versions:
            v_clean = v[6:] if v.startswith("python") else v
            if v_clean.startswith(prefix):
                v_match = re.match(r"(\d+\.\d+\.\d+)", v_clean)
                if v_match:
                    patch = v_match.group(1)
                    patch_prefix = f"python{patch}"
                    if patch_prefix not in groups:
                        groups[patch_prefix] = 0
                    groups[patch_prefix] += 1
        
        print(f"{BOLD}{filter_str}{RESET} versions:")
        for patch in sorted(groups.keys(), key=lambda x: [int(i) for i in re.findall(r"\d+", x)], reverse=True):
            hint = _("python_list_level2_hint", " (Use {BOLD}PYTHON --py-list {prefix}{RESET} to see specific {count} versions)", 
                     BOLD=BOLD, RESET=RESET, prefix=patch, count=groups[patch])
            print(f"  - {patch} ({groups[patch]}){hint}")

    elif re.match(r"^python\d+\.\d+\.\d+$", filter_str):
        # Level 3: platform variants
        prefix = filter_str[6:]
        matches = []
        for v in remote_versions:
            v_clean = v[6:] if v.startswith("python") else v
            if v_clean.startswith(prefix):
                matches.append(v)
        
        print(f"{BOLD}{filter_str}{RESET} variants:")
        for v in sorted(matches):
            status = f" ({_('python_status_installed', 'installed')})" if v in installed else ""
            print(f"  - {v}{status}")
            
    else:
        # Regex search
        try:
            pattern = re.compile(filter_str)
            matches = [v for v in remote_versions if pattern.search(v)]
            count = len(matches)
            found_msg = _("python_list_regex_found", "Found {count} versions matching regex '{regex}'.", count=count, regex=filter_str)
            print(f"{BOLD}{found_msg}{RESET}")
            
            display_matches = matches[:100]
            for v in sorted(display_matches):
                status = f" ({_('python_status_installed', 'installed')})" if v in installed else ""
                print(f"  - {v}{status}")
                
            if count > 100:
                from logic.utils import save_list_report
                report_path = save_list_report(matches, save_dir="PYTHON", filename_prefix="python_list")
                capped_msg = _("python_list_regex_capped", " (Showing first 100, full list saved to: {path})", path=report_path)
                print(f"{YELLOW}{capped_msg}{RESET}")
        except re.error as e:
            error_label = _("label_error", "Error")
            print(f"{RED}{BOLD}{error_label}{RESET}: Invalid regex '{filter_str}': {e}")

    # Common hints
    if not filter_str:
        print("\n" + _("python_set_default_hint", "To set the default version for this tool: PYTHON --py-default {version}", version=installed[0] if installed else "3.10.19"))

def _install_version(version, install_dir=None):
    remote_versions = _get_remote_versions()
    
    # Compatibility layer: handle 'python' prefix and platform tags
    from logic.utils import get_system_tag, regularize_version_name
    tag = get_system_tag()
    
    # Try exact match first
    if version in remote_versions:
        final_version = version
    else:
        # Normalize input (removes 'python' prefix)
        v = version
        if v.startswith("python"): v = v[6:]
        
        # If the input already contains the tag, use it as is for fuzzy match
        if v.endswith(tag):
            matches = [s for s in remote_versions if s == v]
        else:
            # Try version-tag
            candidate = f"{v}-{tag}"
            if candidate in remote_versions:
                final_version = candidate
                matches = [candidate]
            else:
                # Try fuzzy match (e.g., 3.10 -> 3.10.15-macos-arm64)
                matches = [s for s in remote_versions if s.startswith(v) and s.endswith(tag)]
        
        if matches:
            matches.sort(key=len, reverse=True)
            final_version = matches[0]
        else:
            final_version = None

    if not final_version:
        error_label = _("label_error", "Error")
        if remote_versions:
            supported_list = ", ".join(remote_versions[:5]) + ("..." if len(remote_versions) > 5 else "")
            msg = _("python_version_not_supported", "Version {version} is not found in remote 'tool' branch.", version=version, supported=supported_list)
            print(f"{BOLD}{RED}{error_label}{RESET}: {msg}")
            v_base = version.split('-')[0]
            if v_base.startswith("python"): v_base = v_base[6:]
            print(_("python_update_hint", "You can use 'PYTHON --py-update --version {v}' to migrate it from astral-sh builds.", v=v_base))
            print(_("python_install_after_update_hint", "Then run: PYTHON --py-install {v}-{tag}", v=v_base, tag=tag))
        else:
            print(f"{RED}{BOLD}{error_label}{RESET}: No versions found on remote 'tool' branch.")
            print(_("python_update_initial_hint", "Please run 'PYTHON --py-update' first to migrate Python builds."))
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
            subprocess.run(["git", "fetch", "origin", "tool"], capture_output=True, cwd=str(project_root))
            
            cmd = ["git", "checkout", "origin/tool", "--", source_dir_rel]
            result = subprocess.run(cmd, capture_output=True, cwd=str(project_root))
            if result.returncode != 0:
                cmd = ["git", "checkout", "tool", "--", source_dir_rel]
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
            install_script = TOOL_INTERNAL / "install.py"
            if install_script.exists():
                v_match = re.search(r"([\d\.]+)-(.*)", version)
                if v_match:
                    v_num = v_match.group(1)
                    v_plat = v_match.group(2)
                    cmd = [sys.executable, str(install_script), "--version", v_num, "--platform", v_plat, "--limit", "1", "--silent-cache"]
                    subprocess.run(cmd, capture_output=True)
                    if (target_parent / version).exists():
                        sys.stdout.write("\r\033[K")
                        success_status = _("python_install_success_status", "Successfully installed")
                        print(f"{GREEN}{BOLD}{success_status}{RESET} {version}")
                        return True

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
