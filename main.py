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
    from proj.lang.utils import get_translation
    from proj.audit.utils import AuditManager, AuditBase
except ImportError:
    def get_color(name, default="\033[0m"): return default
    def get_translation(d, k, default): return default
    class AuditManager:
        def __init__(self, d, **kwargs): pass
        def load(self, n): return {}
        def save(self, n, d): pass
        def print_cache_warning(self, **kwargs): pass
    class AuditBase:
        def __init__(self, am): pass
        def handle_force(self, a): pass

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

# Try to initialize RTL support and override built-in print
try:
    from proj.utils import smart_print, set_rtl_mode
    import builtins
    builtins.print = smart_print
except ImportError:
    def set_rtl_mode(enabled): pass

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
        # Even if installed, check if dependencies are missing
        missing_dep = False
        tool_json_path = tool_dir / "tool.json"
        if tool_json_path.exists():
            with open(tool_json_path, 'r') as f:
                tool_data = json.load(f)
                dependencies = tool_data.get("dependencies", [])
                for dep in dependencies:
                    dep_dir = tool_parent_dir / dep
                    dep_link = bin_dir / dep
                    if not (dep_dir.exists() and (dep_link.exists() or dep_link.is_symlink())):
                        missing_dep = True
                        break
        
    if not missing_dep:
        success_label = _("install_success_label", "Success")
        print(f"{BOLD}{GREEN}{success_label}{RESET}: " + _("already_installed", "{name} is already installed.", name=tool_name))
        return
    else:
        print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("missing_deps_reinstall", "Tool '{name}' is installed but missing dependencies. Re-installing...", name=tool_name))

    # Add a blank line between tools for better readability
    install_header = _("install_header", "\n--- Installing {name} tool ---", name=tool_name)
    print(f"{BLUE}{BOLD}{install_header}{RESET}")
    
    # 0. Validate against global tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
            if tool_name not in registry.get("tools", {}):
                print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("tool_not_in_registry", "Tool '{name}' is not in the global registry.", name=tool_name))
                return
    else:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("registry_error", "Global tool.json not found."))
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
                success_msg = _("retrieved_success_remote_only", "Successfully retrieved {name} tool", name=tool_name)
                print(f"{BOLD}{GREEN}{success_msg}{RESET}: " + _("retrieved_from", "remote '{branch}' branch{url}", branch=branch_info, url=url_info))
            else:
                # If remote fails, try local tool branch
                subprocess.run(["git", "checkout", "tool", "--", f"tool/{tool_name}"], check=True, capture_output=True, cwd=str(project_root))
                success_msg = _("retrieved_success_local_only", "Successfully retrieved {name} tool", name=tool_name)
                print(f"{BOLD}{GREEN}{success_msg}{RESET}: " + _("retrieved_from", "local '{branch}' branch", branch="tool"))
        except subprocess.CalledProcessError as e:
            # Fallback for old branch structure or if tool is in root
            try:
                result = subprocess.run(["git", "checkout", "origin/tool", "--", tool_name], capture_output=True, cwd=str(project_root))
                if result.returncode == 0:
                    # Move from root to tool/
                    shutil.move(str(project_root / tool_name), str(tool_dir))
                    success_msg = _("retrieved_success_root_only", "Successfully retrieved {name} tool", name=tool_name)
                    print(f"{BOLD}{GREEN}{success_msg}{RESET}: " + _("moved_to_tool", "from 'tool' branch (root) and moved to tool/ folder."))
                else:
                    fail_msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
                    print(f"{BOLD}{RED}{fail_msg}{RESET}: " + _("retrieve_error_msg", "Error retrieving: {error}", error=e))
                    return
            except Exception as e2:
                fail_msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
                print(f"{BOLD}{RED}{fail_msg}{RESET}: " + _("retrieve_error_msg", "Error retrieving: {error}", error=e2))
                return

    if not tool_dir.exists():
        fail_msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
        print(f"{BOLD}{RED}{fail_msg}{RESET}: " + _("tool_dir_not_found", "Error: Tool directory still not found after download attempt."))
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
                    dep_msg = _("installing_dep", "Installing dependency for {name} tool: {dep} tool", name=tool_name, dep=dep)
                    print(f"{BLUE}{BOLD}{dep_msg}{RESET}")
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
                warning_label = _("warning_label", "Warning")
                print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("python_not_found", "PYTHON tool not found. Skipping pip dependencies."))
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
                            warning_label = _("warning_label", "Warning")
                            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("pip_warning_permissions", "Warning: pip install failed due to permissions."))
                            print(_("pip_warning_retry", "Please try running with 'all' permissions."))
                        else:
                            error_label = _("error_label", "Error")
                            print(f"{BOLD}{RED}{error_label}{RESET}: " + _("pip_error", "Warning: pip install failed with error:\n{error}", error=result.stderr))
                    else:
                        success_label = _("pip_success_label", "Success")
                        print(f"{BOLD}{GREEN}{success_label}{RESET}: " + _("pip_success", "Successfully installed pip dependencies for {name} tool.", name=tool_name))
        except Exception as e:
            warning_label = _("warning_label", "Warning")
            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("pip_failed", "Failed to install pip dependencies for {name} tool: {error}", name=tool_name, error=e))

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

if not python_tool_dir.exists():
    print(f"\033[1;31m错误\033[0m: 工具 'PYTHON' 未安装.")
    print(f"该工具 '{tool_name}' 依赖于 PYTHON 工具。")
    print(f"请先运行: TOOL install PYTHON")
    print(f"然后再运行: PYTHON install 3.10.19")
    print(f"最后再运行: TOOL install {tool_name} (以恢复依赖版本)")
    sys.exit(1)

sys.path.append(str(python_tool_dir))

try:
    from proj.utils import get_python_exec
    python_exec = get_python_exec()
    if not os.path.exists(python_exec) and python_exec != "python3":
         print(f"\033[1;33m警告\033[0m: 在 {{python_exec}} 未找到首选的 Python 执行文件。")
         print(f"正在尝试通过 {{tool_name}} 的设置程序进行恢复...")
         setup_py = project_root / "tool" / {repr(tool_name)} / "setup.py"
         if setup_py.exists():
             subprocess.run([sys.executable, str(setup_py)], cwd=str(project_root))
             python_exec = get_python_exec() # Retry
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
        
        success_status = _("python_install_success_status", "Successfully installed")
        print(f"{GREEN}{BOLD}{success_status}{RESET} {tool_name}" + _("shortcut_created", ": shortcut created at {path}", path=link_path))
        
        # 5. Handle PATH registration
        register_path(bin_dir)
    except OSError as e:
        error_label = _("error_label", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: " + _("shortcut_error", "Error creating shortcut for {name}: {error}", name=tool_name, error=e))

    # 6. Run tool setup if setup.py exists
    setup_py = tool_dir / "setup.py"
    if setup_py.exists():
        action_label = _("label_fetching", "Running") # or add label_running
        print(f"{BLUE}{BOLD}{action_label}{RESET} " + _("running_setup", "setup for {name} tool...", name=tool_name))
        try:
            # Run setup.py using the system python3
            subprocess.run([sys.executable, str(setup_py)], check=True, cwd=str(project_root))
            success_status = _("python_install_success_status", "Successfully ran")
            print(f"{BOLD}{GREEN}{success_status}{RESET} " + _("setup_success", "setup for {name} tool.", name=tool_name))
        except Exception as e:
            warning_label = _("warning_label", "Warning")
            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("setup_failed", "Setup for {name} tool failed: {error}", name=tool_name, error=e))

def uninstall_tool(tool_name, force_yes=False):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / "tool" / tool_name
    bin_dir = project_root / "bin"
    link_path = bin_dir / tool_name
    
    if not tool_dir.exists():
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("tool_not_found_local", "Tool '{name}' is not installed.", name=tool_name))
        return

    if not force_yes:
        if sys.stdin.isatty():
            confirm = input(_("confirm_uninstall", "Are you sure you want to uninstall '{name}'? (y/N): ", name=tool_name))
            if confirm.lower() not in ['y', 'yes']:
                print(_("uninstall_cancelled", "Uninstall cancelled."))
                return
        else:
            print(_("non_interactive_skip", "Non-interactive session, skipping confirmation. Use -y to force."))
            return

    un_msg = _("uninstalling_header", "Uninstalling {name} tool...", name=tool_name)
    print(f"{BLUE}{BOLD}{un_msg}{RESET}")
    
    # 1. Remove from bin
    if link_path.exists() or link_path.is_symlink():
        try:
            os.remove(link_path)
            print(_("removed_shortcut", "Removed shortcut at {path}", path=link_path))
        except Exception as e:
            print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("remove_shortcut_failed", "Failed to remove shortcut: {error}", error=e))

    # 2. Remove tool directory
    try:
        shutil.rmtree(tool_dir)
        print(_("removed_tool_dir", "Removed tool directory at {path}", path=tool_dir))
    except Exception as e:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("remove_tool_dir_failed", "Failed to remove tool directory: {error}", error=e))

    success_status = _("uninstall_success_status", "Successfully uninstalled")
    print(f"{BOLD}{GREEN}{success_status}{RESET} {tool_name}")

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
    config_path = data_dir / "config.json"
    
    if key == "language":
        # Validate language code
        lang = value.lower()
        if lang != "en":
            # Check if audit file or translation file exists
            audit_path = project_root / "data" / "audit" / "lang" / f"audit_{lang}.json"
            trans_path = project_root / "proj" / "translation" / f"{lang}.json"
            if not audit_path.exists() and not trans_path.exists():
                # Suggest similar languages
                try:
                    from proj.utils import get_close_matches
                    from proj.lang_auditor import LangAuditor
                    auditor = LangAuditor(project_root)
                    audited_langs = auditor.list_audited_languages()
                    possibilities = ["en"] + audited_langs
                    matches = get_close_matches(lang, possibilities)
                    
                    error_label = f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}"
                    
                    en_names = {
                        "en": "English", "zh": "Chinese", "ar": "Arabic", "he": "Hebrew",
                        "fa": "Persian", "ja": "Japanese", "ko": "Korean", "fr": "French",
                        "de": "German", "es": "Spanish", "it": "Italian", "ru": "Russian"
                    }

                    if matches:
                        msg = _("lang_error_not_found", "Language '{lang}' not found. Did you mean: {matches}?", lang=lang, matches=", ".join(matches))
                        print(f"{error_label}: {msg}")
                        print(_("lang_suggest_list", "You can also use 'TOOL lang --list' to see all supported languages."))
                    else:
                        all_langs = []
                        for l in possibilities:
                            name = en_names.get(l, l)
                            localized_name = get_translation(str(SHARED_PROJ_DIR), f"lang_name_{l}", name)
                            all_langs.append(f"{localized_name}({l})")
                        
                        msg = _("lang_error_not_found_no_suggest", "Language '{lang}' not found. Supported: {all}", lang=lang, all=", ".join(all_langs))
                        print(f"{error_label}: {msg}")
                except Exception as e:
                    error_label = f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}"
                    msg = _("lang_error_not_found_simple", "Language '{lang}' not found.", lang=lang)
                    print(f"{error_label}: {msg}")
                return # Abort update
    
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
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("registry_error", "Global tool.json not found."))
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
            
    lines = []
    lines.append(_("rule_header_main", "--- AI AGENT TOOL RULES ---"))
    lines.append(_("rule_critical_note", "CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations."))
    lines.append(_("rule_efficiency_note", "This ensures code consistency and improves development efficiency. If issues arise during mutual use, the problematic tools can be improved immediately."))
    lines.append("\n" + _("rule_installed_header", "[INSTALLED TOOLS - Use these directly]"))
    for name, info in installed_tools:
        # Try to get translation from tool's own directory first
        tool_proj_dir = project_root / "tool" / name / "proj"
        desc = get_translation(str(tool_proj_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_proj_dir), f"tool_{name}_purpose", info.get('purpose'))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_available_header", "[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]"))
    for name, info in available_tools:
        # For available tools (not yet installed locally), we fall back to root or English defaults
        desc = _(f"tool_{name}_desc", info.get('description'))
        purpose = _(f"tool_{name}_purpose", info.get('purpose'))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_guidelines_header", "[LOCALIZATION & DEVELOPMENT GUIDELINES]"))
    lines.append("- " + _("rule_guideline_1", "**Multi-language Support**: Tools should support localization via a 'proj/translation.json' file."))
    lines.append("- " + _("rule_guideline_2", "**Fallback & Testing**: Always use the `_()` translation helper. English strings MUST be provided as default arguments within the code; **DO NOT include 'en' sections in translation JSON files**. Testing MUST be done on the 'test' branch; after each test, the 'test' branch should be re-synced from 'main'."))
    lines.append("- " + _("rule_guideline_3", "**Shared Logic**: Standardize utilities (like platform detection or version mapping) in the root `proj/` directory to avoid duplicate implementations across different tools."))
    lines.append("- " + _("rule_guideline_4", "**Dependency Management**: Define dependencies in the tool's 'tool.json'. The 'TOOL' manager will automatically install them."))
    lines.append("- " + _("rule_guideline_5", "**Color & Status Style**: Use Bold status labels at line starts. Only the status label (e.g., **Successfully**) should be colored and bolded. Use **Green** for success, **Blue** for progress (including uninstalling), **Red** for errors, and **Yellow** for warnings. Reference colors via `proj.config.get_color`."))
    
    lines.append("\n" + _("rule_note_execution", "NOTE: To use a tool, ensure its executable name (e.g., 'USERINPUT') is called directly in the terminal."))
    lines.append("--------------------------")
    
    output = "\n".join(lines)
    print(output)
    
    # Copy to clipboard
    if sys.platform == "darwin":
        try:
            subprocess.run('pbcopy', input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
            print(f"\n{BOLD}{BLUE}" + _("rule_copied", "Rules have been copied to clipboard.") + f"{RESET}")
        except (FileNotFoundError, subprocess.CalledProcessError): pass
    elif sys.platform == "linux":
        try:
            subprocess.run('xclip -selection clipboard', shell=True, input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
            print(f"\n{BOLD}{BLUE}" + _("rule_copied", "Rules have been copied to clipboard.") + f"{RESET}")
        except (FileNotFoundError, subprocess.CalledProcessError): pass

def sync_branches():
    """Synchronize core files from 'tool' to 'main', then overwrite 'test' with 'main'."""
    project_root = Path(__file__).parent.absolute()
    core_files = [
        "main.py",
        "setup.py",
        "README.md",
        ".gitignore",
        ".gitattributes",
        "proj",
        "test",
        "todo"
    ]
    
    # Get current branch
    try:
        current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except subprocess.CalledProcessError:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("not_git_repo", "Not a git repository."))
        return
    
    # 1. Check for uncommitted changes
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("sync_uncommitted", "There are uncommitted changes in '{branch}'. Please commit them first.", branch=current_branch))
            return
    except subprocess.CalledProcessError: pass

    # 2. Sync to main
    sync_label = _("sync_to_main_label", "Syncing")
    print(f"{BOLD}{BLUE}{sync_label}{RESET} to 'main' branch...")
    
    commands = [
        ["git", "checkout", "main"],
        ["git", "checkout", current_branch, "--"] + core_files,
        ["git", "commit", "-m", f"Sync core files from {current_branch} branch"],
        ["git", "branch", "-D", "test"],
        ["git", "checkout", "-b", "test"],
        ["git", "checkout", current_branch]
    ]
    
    for cmd in commands:
        try:
            if cmd[0] == "git" and cmd[1] == "branch" and cmd[2] == "-D":
                subprocess.run(cmd, stderr=subprocess.DEVNULL, cwd=str(project_root))
            elif cmd[0] == "git" and cmd[1] == "commit":
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
                if res.returncode != 0 and "nothing to commit" not in res.stdout:
                    raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
            else:
                subprocess.run(cmd, check=True, cwd=str(project_root))
            
            # Special logic after switching to main
            if cmd == ["git", "checkout", "main"]:
                # Ensure main has restricted .gitignore
                gitignore_content = """# Deny all
*
# Allow specific files
!README.md
!main.py
!setup.py
!tool.json
!bin/
!bin/**
!proj/
!proj/**
!test/
!test/**
!todo/
!todo/**
!.gitignore
"""
                with open(project_root / ".gitignore", 'w') as f:
                    f.write(gitignore_content)
                
                # Cleanup unwanted folders in main
                for d in ["data", "tmp", "tool", "resource"]:
                    p = project_root / d
                    if p.exists() and p.is_dir():
                        shutil.rmtree(p)
                        subprocess.run(["git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
        except subprocess.CalledProcessError as e:
            error_label = _("error_label", "Error")
            print(f"{BOLD}{RED}{error_label}{RESET}: Command failed: {' '.join(cmd)}")
            print(f"Details: {e.output}")
            return

    success_status = _("sync_success_status", "Successfully synced")
    print(f"{BOLD}{GREEN}{success_status}{RESET} branches. Ready for testing on 'test'.")

            # After checking out core files to main, swap the .gitignore
            if cmd == ["git", "checkout", current_branch, "--"] + core_files:
                if restricted_gitignore.exists():
                    shutil.copy(restricted_gitignore, project_root / ".gitignore")
                    subprocess.run(["git", "add", ".gitignore"], cwd=str(project_root), check=True)

        except subprocess.CalledProcessError as e:
            print(f"{BOLD}{RED}" + _("sync_error_label", "Error during sync") + f"{RESET} at step {' '.join(cmd)}: {e}")
            subprocess.run(["git", "checkout", current_branch], stderr=subprocess.DEVNULL, cwd=str(project_root))
            return

    print(f"{BOLD}{GREEN}" + _("sync_complete_label", "Synchronization complete") + f"{RESET}!")

import argparse

def main():
    # 1. Initialize RTL mode based on current language
    current_lang = os.environ.get("TOOL_LANGUAGE")
    if not current_lang:
        config_path = ROOT_PROJECT_ROOT / "data" / "config.json"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    current_lang = json.load(f).get("language", "en")
            except Exception: pass
    
    if current_lang in ["ar", "he", "fa"]:
        set_rtl_mode(True)

    parser = argparse.ArgumentParser(
        prog="TOOL",
        description=_("tool_description", "AITerminalTools - A unified management system for AI tools."),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_("tool_epilog", """
Examples:
  TOOL install USERINPUT        # Install a specific tool
  TOOL test USERINPUT           # Run unit tests for a tool
  TOOL rule                     # Generate AI agent guidelines
  TOOL lang set zh              # Set global language preference
        """))
    
    subparsers = parser.add_subparsers(dest="command", help=_("subcommand_help", "Available commands"))

    # Install command
    install_parser = subparsers.add_parser("install", help=_("install_help", "Install a tool and its dependencies"))
    install_parser.add_argument("tool_name", help=_("install_tool_name_help", "Name of the tool to install"))

    # Uninstall command
    uninstall_parser = subparsers.add_parser("uninstall", help=_("uninstall_help", "Uninstall a tool"))
    uninstall_parser.add_argument("tool_name", help=_("uninstall_tool_name_help", "Name of the tool to uninstall"))
    uninstall_parser.add_argument("-y", "--yes", action="store_true", help=_("uninstall_yes_help", "Don't ask for confirmation"))

    # Test command
    test_parser = subparsers.add_parser("test", help=_("test_help", "Run unit tests for a tool"))
    test_parser.add_argument("tool_name", nargs="?", default="root", help=_("test_tool_name_help", "Name of the tool to test (default: root)"))
    test_parser.add_argument("--list", action="store_true", help=_("test_list_help", "List available tests"))
    test_parser.add_argument("--range", nargs=2, type=int, metavar=("START", "END"), help=_("test_range_help", "Range of test IDs to run"))
    test_parser.add_argument("--max", type=int, default=3, help=_("test_max_help", "Maximum concurrent test jobs (default: 3)"))
    test_parser.add_argument("--timeout", type=int, default=60, help=_("test_timeout_help", "Timeout for each test in seconds (default: 60)"))

    # Audit command
    audit_parser = subparsers.add_parser("audit-lang", help=_("audit_help", "Audit language translation coverage"))
    audit_parser.add_argument("lang_code", help=_("audit_lang_code_help", "Language code to audit (e.g., en, zh)"))
    audit_parser.add_argument("--force", action="store_true", help=_("audit_force_help", "Force a full re-scan"))

    # Lang command
    lang_root_parser = subparsers.add_parser("lang", help=_("lang_help", "Manage display language"))
    # Add optional arguments for --set and --list to support the user's desired syntax
    lang_root_parser.add_argument("--set", dest="lang_set_val", help=_("lang_set_help", "Set display language"))
    lang_root_parser.add_argument("--list", dest="lang_list", action="store_true", help=_("lang_list_help", "List supported languages and their coverage"))
    
    lang_subparsers = lang_root_parser.add_subparsers(dest="lang_command", help=_("lang_subcommand_help", "Language subcommands"))
    
    lang_set_parser = lang_subparsers.add_parser("set", help=_("lang_set_help", "Set display language"))
    lang_set_parser.add_argument("lang_code", help=_("lang_code_help", "Language code (e.g., en, zh, ar)"))
    
    lang_subparsers.add_parser("list", help=_("lang_list_help", "List supported languages and their coverage"))

    # Rule command
    subparsers.add_parser("rule", help=_("rule_help", "Generate AI agent tool rules"))

    # Sync command
    subparsers.add_parser("sync", help="Synchronize core files across tool, main, and test branches")

    # Config command
    config_parser = subparsers.add_parser("config", help=_("config_help", "Manage global configurations"))
    config_subparsers = config_parser.add_subparsers(dest="subcommand", help=_("config_subcommand_help", "Config subcommands"))
    
    config_lang_parser = config_subparsers.add_parser("set-lang", help=_("config_set_lang_help", "Set global language preference"))
    config_lang_parser.add_argument("lang_code", help=_("config_lang_code_help", "Language code (e.g., en, zh)"))

    test_config_parser = config_subparsers.add_parser("test", help=_("config_test_help", "Test configuration"))
    test_config_parser.add_argument("--max-reports", type=int, help=_("config_test_max_reports_help", "Maximum number of test reports to keep"))

    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if args.command == "install":
        install_tool(args.tool_name)
    elif args.command == "uninstall":
        uninstall_tool(args.tool_name, args.yes)
    elif args.command == "test":
        _test_tool_with_args(args)
    elif args.command == "audit-lang":
        _audit_lang(args.lang_code, force=args.force)
    elif args.command == "lang":
        if args.lang_set_val:
            update_config("language", args.lang_set_val)
        elif args.lang_list or args.lang_command == "list":
            _list_languages()
        elif args.lang_command == "set":
            update_config("language", args.lang_code)
        else:
            _show_current_language()
    elif args.command == "rule":
        generate_ai_rule()
    elif args.command == "sync":
        sync_branches()
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
    
    if args.tool_name == "root":
        tool_dir = project_root
    else:
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

def _audit_lang(lang_code, force=False):
    project_root = Path(__file__).parent.absolute()
    
    # 1. Map lang_code to lang_name
    lang_name = _(f"lang_name_{lang_code}", lang_code)
    
    # 2. Print initial "scanning" message with ellipsis
    sys.path.append(str(project_root))
    try:
        from proj.lang.audit import LangAuditor
        from proj.utils import get_rate_color
    except ImportError:
        print(f"\n{RED}" + _("audit_import_error", "Error: Could not import LangAuditor.") + f"{RESET}")
        return

    # Handle --force
    if force:
        audit_file = project_root / "data" / "audit" / "lang" / f"audit_{lang_code}.json"
        if audit_file.exists():
            audit_file.unlink()

    auditor = LangAuditor(project_root, lang_code)
    
    if auditor.cache_file.exists():
        msg = _("audit_using_cache", "Using cached audit report for {lang} ({lang_name})...", lang=lang_code, lang_name=lang_name)
    else:
        msg = _("audit_scanning", "Scanning translation coverage for {lang} ({lang_name})...", lang=lang_code, lang_name=lang_name)
    
    print(f"{BLUE}{msg}{RESET}", end="", flush=True)

    results, _unused = auditor.audit()
    summary = results.get("summary", {})
    
    # 3. Completion message (default style)
    print("\r" + " " * 80 + "\r", end="") # Clear line
    if _unused:
        msg = _("audit_using_cache_done", "Audit report for {lang} ({lang_name}) retrieved.", lang=lang_code, lang_name=lang_name)
    else:
        msg = _("audit_scanning_done", "Translation audit scan for {lang} ({lang_name}) complete.", lang=lang_code, lang_name=lang_name)
    print(msg)

    # 4. Colorize percentages using threshold logic from utils
    colors_dict = {"BOLD": BOLD, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW, "RED": RED, "RESET": RESET}
    
    rate_keys = summary.get("completion_rate_keys", "0%")
    rate_refs = summary.get("completion_rate_refs", "0%")
    
    color_keys = get_rate_color(rate_keys, colors_dict)
    color_refs = get_rate_color(rate_refs, colors_dict)
    
    # 5. Summary output
    print(_("audit_summary_keys", "{rate} of keys support {lang} ({lang_name}) translation ({supported}/{total})",
            rate=f"{color_keys}{rate_keys}{RESET}", supported=summary.get("supported_keys"), 
            total=summary.get("total_keys"), lang=lang_code, lang_name=lang_name))
            
    print(_("audit_summary_refs", "{rate} of references support {lang} ({lang_name}) translation ({supported}/{total})",
            rate=f"{color_refs}{rate_refs}{RESET}", supported=summary.get("supported_references"), 
            total=summary.get("total_references"), lang=lang_code, lang_name=lang_name))
    
    print(_("audit_report_path", "Detailed report saved to: {path}", path=auditor.cache_file))

    # 6. Cache warning and force re-scan tip if using cache
    if _unused:
        audit_dir = project_root / "data" / "audit" / "lang"
        audit_mgr = AuditManager(audit_dir, component_name="LANG_AUDIT", audit_command=f"TOOL audit-lang {lang_code}")
        # Note: --force is handled at the beginning of audit_lang_coverage
        audit_mgr.print_cache_warning()

def _show_current_language():
    """Display the current language and its code."""
    project_root = Path(__file__).parent.absolute()
    # 1. Get language from config
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                current_lang = json.load(f).get("language", "en")
        except Exception: pass
    
    # 2. Get localized name
    en_names = {
        "en": "English", "zh": "Chinese", "ar": "Arabic", "he": "Hebrew",
        "fa": "Persian", "ja": "Japanese", "ko": "Korean", "fr": "French",
        "de": "German", "es": "Spanish", "it": "Italian", "ru": "Russian"
    }
    default_name = en_names.get(current_lang, current_lang)
    localized_name = _(f"lang_name_{current_lang}", default_name)
    
    print(f"{localized_name} ({current_lang})")

def _list_languages():
    project_root = Path(__file__).parent.absolute()
    sys.path.append(str(project_root))
    
    try:
        from proj.lang_auditor import LangAuditor
        from proj.utils import get_rate_color, get_display_width
    except ImportError:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("audit_import_error", "Could not import LangAuditor."))
        return

    auditor = LangAuditor(project_root)
    audited_langs = auditor.list_audited_languages()
    
    # Global config for current language
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                current_lang = json.load(f).get("language", "en")
        except Exception: pass

    # Prepare data for table
    rows = []
    
    # Language names mapping for English defaults
    en_names = {
        "en": "English",
        "zh": "Chinese",
        "ar": "Arabic",
        "he": "Hebrew",
        "fa": "Persian",
        "ja": "Japanese",
        "ko": "Korean",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "it": "Italian",
        "ru": "Russian"
    }

    # Always include English
    rows.append({
        "code": "en",
        "name": _("lang_name_en", "English"),
        "keys": _("lang_default", "default"),
        "refs": _("lang_default", "default"),
        "is_current": current_lang == "en"
    })
    
    colors_dict = {"BOLD": BOLD, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW, "RED": RED, "RESET": RESET}

    for lang in audited_langs:
        if lang == "en": continue
        
        default_name = en_names.get(lang, lang)
        lang_name = _(f"lang_name_{lang}", default_name)
        
        # Load audit data
        results, _unused = LangAuditor(project_root, lang).audit()
        summary = results.get("summary", {})
        
        rate_keys = summary.get("completion_rate_keys", "0%")
        rate_refs = summary.get("completion_rate_refs", "0%")
        
        color_keys = get_rate_color(rate_keys, colors_dict)
        color_refs = get_rate_color(rate_refs, colors_dict)
        
        rows.append({
            "code": lang,
            "name": lang_name,
            "keys": f"{color_keys}{rate_keys}{RESET}",
            "refs": f"{color_refs}{rate_refs}{RESET}",
            "is_current": current_lang == lang
        })

    # Print Table
    header_name = _("lang_table_name", "Language")
    header_keys = _("lang_table_keys", "Key Coverage")
    header_refs = _("lang_table_refs", "Ref Coverage")
    
    headers = [header_name, header_keys, header_refs]
    table_rows = []
    
    for r in rows:
        indicator = " *" if r["is_current"] else ""
        table_rows.append([
            f"{r['name']}({r['code']})",
            r["keys"],
            r["refs"] + indicator
        ])

    print("\n" + _("lang_list_header", "Supported Languages:"))
    
    try:
        terminal_width = os.get_terminal_size().columns
    except (AttributeError, OSError):
        terminal_width = 80

    from proj.utils import format_table
    table_str, report_path = format_table(headers, table_rows, max_width=terminal_width, save_dir="lang")
    print(table_str)
    
    if report_path and "..." in table_str:
        print("\n" + _("full_report_saved", "Full report saved to: {path}", path=report_path))
    
    print("\n" + _("lang_table_footer_star", "*: current language"))
    print(_("lang_table_footer_keys", "Keys: Total number of unique translation strings found in code."))
    print(_("lang_table_footer_refs", "References: Total number of times translation strings are used in code."))
    
    print("\n" + _("lang_audit_instruction", "To audit a specific language coverage: TOOL audit-lang <lang_code>"))
    
    # Dynamic dev instruction with example
    example_lang = "zh" if "zh" in audited_langs else (audited_langs[0] if audited_langs else "en")
    example_path = f"proj/translation/<lang_code>/already_installed"
    if example_lang != "en":
        try:
            results, _unused_cached = LangAuditor(project_root, example_lang).audit()
            if results.get("missing_translation"):
                example_path = results["missing_translation"][0]
            elif results.get("entries"):
                example_path = results["entries"][0].get("logical_path", example_path)
        except Exception: pass

    # Replace <lang_code> in example path for clarity
    example_path = example_path.replace(example_lang, "<lang_code>")
    
    print(_("lang_dev_instruction", "To support a new language: Run audit for the new language (e.g., TOOL audit-lang <lang_code>), then create translation JSONs based on each entry in the 'missing_translation' field of the detailed report JSON. For example, if you see logical path '{path}', create/edit the corresponding JSON file and add the key with its translation.", path=example_path))

if __name__ == "__main__":
    main()
