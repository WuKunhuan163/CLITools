#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import stat
import shutil
from pathlib import Path

# Try to import colors and shared utils from proj
try:
    from proj.config import get_color
    from proj.language_utils import get_translation
except ImportError:
    def get_color(name, default="\033[0m"): return default
    def get_translation(d, k, default): return default

# Define commonly used colors with defaults
RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", RESET)
BOLD = get_color("BOLD", RESET)
BLUE = get_color("BLUE", RESET)
YELLOW = get_color("YELLOW", RESET)
RED = get_color("RED", RESET)

# Root project directory
ROOT_PROJECT_ROOT = Path(__file__).parent.absolute()
SHARED_PROJ_DIR = ROOT_PROJECT_ROOT / "proj"

def _(translation_key, default, **kwargs):
    text = get_translation(str(SHARED_PROJ_DIR), translation_key, default)
    return text.format(**kwargs)

def install_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    # Install tools into a 'tool' subdirectory
    tool_parent_dir = project_root / "tool"
    tool_parent_dir.mkdir(exist_ok=True)
    tool_dir = tool_parent_dir / tool_name
    bin_dir = project_root / "bin"
    
    # Check if already installed
    link_path = bin_dir / tool_name
    if tool_dir.exists() and (link_path.exists() or link_path.is_symlink()):
        print(_("already_installed", "{name} is already installed.", name=tool_name))
        return

    # Add a blank line between tools for better readability
    print(_("install_header", "\n--- Installing {name} tool ---", name=tool_name))
    
    # 0. Validate against global tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
            if tool_name not in registry.get("tools", {}):
                print(f"{RED}" + _("tool_not_in_registry", "Error: Tool '{name}' is not in the global registry.", name=tool_name) + f"{RESET}")
                return
    else:
        print(f"{RED}" + _("registry_error", "Error: Global tool.json not found.") + f"{RESET}")
        return

    # 1. If tool directory doesn't exist, try to download from GitHub 'tool' branch
    if not tool_dir.exists():
        print(_("tool_not_found", "Tool {name} not found locally. Attempting to fetch...", name=tool_name))
        
        # Determine remote URL if possible
        remote_url = ""
        try:
            remotes = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True, cwd=str(project_root)).stdout
            for line in remotes.splitlines():
                if "origin" in line and "(fetch)" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        base_url = parts[1].replace(".git", "")
                        remote_url = f"{base_url}/tree/tool/tool/{tool_name}"
                        break
        except Exception:
            pass

        try:
            # Try to checkout from origin/tool - note the path is tool/<name> in the branch
            result = subprocess.run(["git", "checkout", "origin/tool", "--", f"tool/{tool_name}"], capture_output=True, cwd=str(project_root))
            if result.returncode == 0:
                branch_info = "origin/tool"
                url_info = f": {remote_url}" if remote_url else ""
                msg = _("retrieved_success_remote_only", "Successfully retrieved {name} tool", name=tool_name)
                print(f"{BOLD}{BLUE}{msg}{RESET}: " + _("retrieved_from", "remote '{branch}' branch{url}", branch=branch_info, url=url_info))
            else:
                # If remote fails, try local tool branch
                subprocess.run(["git", "checkout", "tool", "--", f"tool/{tool_name}"], check=True, capture_output=True, cwd=str(project_root))
                msg = _("retrieved_success_local_only", "Successfully retrieved {name} tool", name=tool_name)
                print(f"{BOLD}{BLUE}{msg}{RESET}: " + _("retrieved_from", "local '{branch}' branch", branch="tool"))
        except subprocess.CalledProcessError as e:
            # Fallback for old branch structure or if tool is in root
            try:
                result = subprocess.run(["git", "checkout", "origin/tool", "--", tool_name], capture_output=True, cwd=str(project_root))
                if result.returncode == 0:
                    # Move from root to tool/
                    shutil.move(str(project_root / tool_name), str(tool_dir))
                    msg = _("retrieved_success_root_only", "Successfully retrieved {name} tool", name=tool_name)
                    print(f"{BOLD}{BLUE}{msg}{RESET}: " + _("moved_to_tool", "from 'tool' branch (root) and moved to tool/ folder."))
                else:
                    msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
                    print(f"{BOLD}{RED}{msg}{RESET}: " + _("retrieve_error_msg", "Error retrieving: {error}", error=e))
                    return
            except Exception as e2:
                msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
                print(f"{BOLD}{RED}{msg}{RESET}: " + _("retrieve_error_msg", "Error retrieving: {error}", error=e2))
                return

    if not tool_dir.exists():
        msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
        print(f"{BOLD}{RED}{msg}{RESET}: " + _("tool_dir_not_found", "Error: Tool directory still not found after download attempt."))
        return

    # 2. Parse tool.json for dependencies
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        with open(tool_json_path, 'r') as f:
            tool_data = json.load(f)
            dependencies = tool_data.get("dependencies", [])
            for dep in dependencies:
                # Pre-check dependency
                dep_dir = tool_parent_dir / dep
                dep_link = bin_dir / dep
                if not (dep_dir.exists() and (dep_link.exists() or dep_link.is_symlink())):
                    print(_("installing_dep", "Installing dependency for {name} tool: {dep} tool", name=tool_name, dep=dep))
                    install_tool(dep)

    # 2.1 Handle pip dependencies if proj/requirements.txt exists
    requirements_path = tool_dir / "proj" / "requirements.txt"
    if not requirements_path.exists():
        requirements_path = tool_dir / "requirements.txt"
    
    if requirements_path.exists():
        try:
            # Use the installed PYTHON tool to get the python executable
            python_tool_dir = project_root / "tool" / "PYTHON"
            if not python_tool_dir.exists():
                print(f"{YELLOW}" + _("python_not_found", "Warning: PYTHON tool not found. Skipping pip dependencies.") + f"{RESET}")
            else:
                # Import get_python_exec from tool/PYTHON/proj/utils.py
                python_utils_path = python_tool_dir / "proj" / "utils.py"
                if python_utils_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("python_utils_mod", str(python_utils_path))
                    python_utils_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(python_utils_mod)
                    python_exec = python_utils_mod.get_python_exec()
                    
                    # Run pip install using the standalone python
                    # Capture output to avoid messy errors on screen
                    result = subprocess.run(
                        [python_exec, "-m", "pip", "install", "-r", str(requirements_path)],
                        capture_output=True, text=True
                    )
                    
                    if result.returncode != 0:
                        if "PermissionError" in result.stderr or "Operation not permitted" in result.stderr:
                            print(f"{YELLOW}" + _("pip_warning_permissions", "Warning: pip install failed due to permissions.") + f"{RESET}")
                            print(_("pip_warning_retry", "Please try running with 'all' permissions."))
                        else:
                            print(f"{RED}" + _("pip_error", "Warning: pip install failed with error:\n{error}", error=result.stderr) + f"{RESET}")
                    else:
                        print(_("pip_success", "Successfully installed pip dependencies for {name} tool.", name=tool_name))
        except Exception as e:
            print(f"{YELLOW}" + _("pip_failed", "Warning: Failed to install pip dependencies for {name} tool: {error}", name=tool_name, error=e) + f"{RESET}")

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
        print(f"{BOLD}{RED}{msg}{RESET}: " + _("tool_main_not_found_msg", "Error: {path} not found in tool directory.", path=main_py))
        return

    # 3. Create bin directory
    bin_dir.mkdir(exist_ok=True)
    
    # 4. Create entry point in bin directory
    link_path = bin_dir / tool_name
    if link_path.exists() or link_path.is_symlink():
        os.remove(link_path)
    
    try:
        # Ensure main.py is executable
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)

        # Check if the tool depends on PYTHON. If so, create a wrapper script.
        use_wrapper = False
        if tool_json_path.exists():
            with open(tool_json_path, 'r') as f:
                tool_data = json.load(f)
                if "PYTHON" in tool_data.get("dependencies", []):
                    use_wrapper = True
        
        if use_wrapper:
            # Create a wrapper script that uses the standalone python
            wrapper_content = f'''#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

# Add the directory containing 'proj' to PYTHONPATH for the subprocess
project_root = Path({repr(str(project_root))})
python_tool_dir = project_root / "tool" / "PYTHON"
sys.path.append(str(python_tool_dir))

try:
    from proj.utils import get_python_exec
    python_exec = get_python_exec()
except ImportError:
    python_exec = "python3"

# Set up environment
env = os.environ.copy()
# Add the project root (containing root 'proj') and tool's directory (containing 'proj') to PYTHONPATH
tool_main = Path({repr(str(main_py))})
env["PYTHONPATH"] = f"{{project_root}}:{{tool_main.parent}}:{{env.get('PYTHONPATH', '')}}"

if __name__ == "__main__":
    result = subprocess.run([python_exec, str(tool_main)] + sys.argv[1:], env=env)
    sys.exit(result.returncode)
'''
            with open(link_path, 'w') as f:
                f.write(wrapper_content)
            os.chmod(link_path, st.st_mode | stat.S_IEXEC)
        else:
            # Traditional symlink
            os.symlink(main_py, link_path)
        
        print(f"{BOLD}{GREEN}" + _("install_success", "Successfully installed {name} tool", name=tool_name) + f"{RESET}" + _("shortcut_created", ": shortcut created at {path}", path=link_path))
        
        # 5. Handle PATH registration
        register_path(bin_dir)
    except OSError as e:
        print(f"{RED}" + _("shortcut_error", "Error creating shortcut for {name}: {error}", name=tool_name, error=e) + f"{RESET}")

def register_path(bin_dir):
    """Add bin_dir to shell profile if not already present."""
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    profiles = []
    if "zsh" in shell:
        profiles.append(home / ".zshrc")
    elif "bash" in shell:
        profiles.append(home / ".bash_profile")
        profiles.append(home / ".bashrc")
    else:
        profiles.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
    
    for profile in profiles:
        if profile.exists():
            with open(profile, 'r') as f:
                content = f.read()
            if str(bin_dir) not in content:
                with open(profile, 'a') as f:
                    f.write(export_cmd)
                print(_("updated_path", "Updated {profile} with PATH.", profile=profile))
            else:
                # Already exists
                pass
    
    # Update current session's os.environ
    if str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:" + os.environ["PATH"]

def update_config(key, value):
    project_root = Path(__file__).parent.absolute()
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    config_path = data_dir / "global_config.json"
    
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception:
            pass
    
    config[key] = value
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    print(_("config_updated", "Global configuration updated: {key} = {value}", key=key, value=value))

def generate_ai_rule():
    project_root = Path(__file__).parent.absolute()
    registry_path = project_root / "tool.json"
    
    if not registry_path.exists():
        print(f"{RED}" + _("registry_error", "Error: Global tool.json not found.") + f"{RESET}")
        return

    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    tools = registry.get("tools", {})
    installed_tools = []
    available_tools = []
    
    for name, info in tools.items():
        if (project_root / "tool" / name).exists():
            installed_tools.append((name, info))
        else:
            available_tools.append((name, info))
            
    print(_("rule_header_main", "--- AI AGENT TOOL RULES ---"))
    print(_("rule_critical_note", "CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations."))
    print(_("rule_efficiency_note", "This ensures consistency, leverages optimized logic, and improves development efficiency."))
    print("\n" + _("rule_installed_header", "[INSTALLED TOOLS - Use these directly]"))
    for name, info in installed_tools:
        print(f"- {name}: {info.get('description')} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=info.get('purpose')) + ")")
        
    print("\n" + _("rule_available_header", "[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]"))
    for name, info in available_tools:
        print(f"- {name}: {info.get('description')} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=info.get('purpose')) + ")")
        
    print("\n" + _("rule_guidelines_header", "[LOCALIZATION & DEVELOPMENT GUIDELINES]"))
    print("- " + _("rule_guideline_1", "**Multi-language Support**: Tools should support localization via a 'proj/translations.json' file."))
    print("- " + _("rule_guideline_2", "**Fallback Mechanism**: Tools must have hardcoded English defaults. If a translation for the user's preferred language (provided via the 'TOOL_LANGUAGE' environment variable) is missing, the tool should fallback to these defaults."))
    print("- " + _("rule_guideline_3", "**Shared Utilities**: Leverage 'PYTHON' tool's 'proj.language_utils' for consistent translation lookups."))
    print("- " + _("rule_guideline_4", "**Dependency Management**: Define dependencies in the tool's 'tool.json'. The 'TOOL' manager will automatically install them."))
    
    print("\n" + _("rule_note_execution", "NOTE: To use a tool, ensure its executable name (e.g., 'USERINPUT') is called directly in the terminal."))
    print("--------------------------")

import argparse

def main():
    parser = argparse.ArgumentParser(
        description=_("tool_description", "AITerminalTools - A unified management system for AI tools."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_("tool_epilog", """
Examples:
  TOOL install USERINPUT        # Install a specific tool
  TOOL test USERINPUT           # Run unit tests for a tool
  TOOL rule                     # Generate AI agent guidelines
  TOOL config set-lang zh       # Set global language preference
        """))
    
    subparsers = parser.add_subparsers(dest="command", help=_("subcommand_help", "Available commands"))

    # Install command
    install_parser = subparsers.add_parser("install", help=_("install_help", "Install a tool and its dependencies"))
    install_parser.add_argument("tool_name", help=_("install_tool_name_help", "Name of the tool to install"))

    # Test command
    test_parser = subparsers.add_parser("test", help=_("test_help", "Run unit tests for a tool"))
    test_parser.add_argument("tool_name", help=_("test_tool_name_help", "Name of the tool to test"))
    test_parser.add_argument("--list", action="store_true", help=_("test_list_help", "List available tests"))
    test_parser.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help=_("test_range_help", "Range of test IDs to run"))
    test_parser.add_argument("--max", type=int, default=3, help=_("test_max_help", "Maximum concurrent test jobs (default: 3)"))
    test_parser.add_argument("--timeout", type=int, default=60, help=_("test_timeout_help", "Timeout for each test in seconds (default: 60)"))

    # Audit command
    audit_parser = subparsers.add_parser("audit-lang", help=_("audit_help", "Audit language translation coverage"))
    audit_parser.add_argument("lang_code", help=_("audit_lang_code_help", "Language code to audit (e.g., en, zh)"))

    # Rule command
    subparsers.add_parser("rule", help=_("rule_help", "Generate AI agent tool rules"))

    # Config command
    config_parser = subparsers.add_parser("config", help=_("config_help", "Manage global configurations"))
    config_subparsers = config_parser.add_subparsers(dest="subcommand", help=_("config_subcommand_help", "Config subcommands"))
    
    lang_parser = config_subparsers.add_parser("set-lang", help=_("config_set_lang_help", "Set global language preference"))
    lang_parser.add_argument("lang_code", help=_("config_lang_code_help", "Language code (e.g., en, zh)"))

    test_config_parser = config_subparsers.add_parser("test", help=_("config_test_help", "Test configuration"))
    test_config_parser.add_argument("--max-reports", type=int, help=_("config_test_max_reports_help", "Maximum number of test reports to keep"))

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "install":
        install_tool(args.tool_name)
    elif args.command == "test":
        _test_tool_with_args(args)
    elif args.command == "audit-lang":
        _audit_lang(args.lang_code)
    elif args.command == "rule":
        generate_ai_rule()
    elif args.command == "config":
        if args.subcommand == "set-lang":
            update_config("language", args.lang_code)
        elif args.subcommand == "test":
            if args.max_reports is not None:
                update_config("test_max_reports", args.max_reports)
            else:
                test_config_parser.print_help()
        else:
            config_parser.print_help()

def _test_tool_with_args(args):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / "tool" / args.tool_name
    
    if not tool_dir.exists():
        print(f"{RED}" + _("test_tool_not_found", "Error: Tool directory {path} not found.", path=tool_dir) + f"{RESET}")
        return

    # Default max_concurrent from tool.json or 1
    max_concurrent = 1
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        try:
            with open(tool_json_path, 'r') as f:
                tool_data = json.load(f)
                max_concurrent = tool_data.get("test_parallel", 1)
        except Exception:
            pass
    
    # Override with --max if provided
    if args.max != 3: # default in argparse was 3, but we want 1 if not specified
        max_concurrent = args.max
    elif args.max == 3 and not (tool_json_path.exists() and "test_parallel" in tool_data):
        # If user didn't provide --max and tool.json doesn't have it, use 1
        max_concurrent = 1

    # Import TestRunner from proj.test_runner
    sys.path.append(str(project_root))
    try:
        from proj.test_runner import TestRunner
    except ImportError:
        print(f"{RED}" + _("test_runner_import_error", "Error: Could not import TestRunner from proj.test_runner.") + f"{RESET}")
        return

    runner = TestRunner(args.tool_name, project_root)
    
    if args.list:
        runner.list_tests()
        return

    start_id = None
    end_id = None
    if args.range:
        start_id = args.range[0]
        end_id = args.range[1]

    runner.run_tests(start_id, end_id, max_concurrent, args.timeout)

def _audit_lang(lang_code):
    project_root = Path(__file__).parent.absolute()
    
    # 1. Print initial "scanning" message with ellipsis
    sys.path.append(str(project_root))
    try:
        from proj.lang_auditor import LangAuditor
    except ImportError:
        print(f"\n{RED}" + _("audit_import_error", "Error: Could not import LangAuditor.") + f"{RESET}")
        return

    auditor = LangAuditor(project_root, lang_code)
    
    # 2. Determine if cached or scanning and print the line
    if auditor.cache_file.exists():
        msg = _("audit_using_cache", "Using cached audit report for {lang}...", lang=lang_code)
    else:
        msg = _("audit_scanning", "Scanning translation coverage for {lang}...", lang=lang_code)
    
    print(f"{BLUE}{msg}{RESET}", end="", flush=True)

    # 3. Perform audit
    results, cached = auditor.audit()
    summary = results.get("summary", {})
    
    # Replace the ellipsis with completed message if needed, or just move to next line
    print("\r" + " " * 80 + "\r", end="") # Clear line
    if cached:
        msg = _("audit_using_cache_done", "Using cached audit report for {lang}.", lang=lang_code)
    else:
        msg = _("audit_scanning_done", "Translation audit scan complete for {lang}.", lang=lang_code)
    print(f"{BLUE}{msg}{RESET}")

    # 4. Compact output according to user feedback
    print(_("audit_summary_keys", "Keys: {supported}/{total} support {lang} ({rate})",
            supported=summary.get("supported_keys"), total=summary.get("total_keys"), lang=lang_code, rate=summary.get("completion_rate_keys")))
    print(_("audit_summary_refs", "References: {supported}/{total} support {lang} ({rate})",
            supported=summary.get("supported_references"), total=summary.get("total_references"), lang=lang_code, rate=summary.get("completion_rate_refs")))
    
    print(_("audit_report_path", "Detailed report saved to: {path}", path=auditor.cache_file))

if __name__ == "__main__":
    main()
