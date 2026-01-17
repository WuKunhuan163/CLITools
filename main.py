#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import stat
import shutil
from pathlib import Path

# Color codes
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Try to import colors and shared utils from proj
try:
    from proj.config import get_color
    from proj.lang.utils import get_translation
    from proj.audit.utils import AuditManager, AuditBase
    
    RESET = get_color("RESET", "\033[0m")
    GREEN = get_color("GREEN", "\033[32m")
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    YELLOW = get_color("YELLOW", "\033[33m")
    RED = get_color("RED", "\033[31m")
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
            success_status = _("python_install_success_status", "Successfully installed")
            print(f"{BOLD}{GREEN}{success_status}{RESET}: " + _("already_installed", "{name} is already installed.", name=tool_name))
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
        
        try:
            # Try to checkout from origin/tool - note the path is tool/<name> in the branch
            result = subprocess.run(["git", "checkout", "origin/tool", "--", f"tool/{tool_name}"], capture_output=True, cwd=str(project_root))
            if result.returncode == 0:
                success_status = _("python_install_success_status", "Successfully retrieved")
                print(f"{BOLD}{GREEN}{success_status}{RESET} {tool_name} " + _("retrieved_from", "from remote '{branch}' branch", branch="origin/tool"))
            else:
                # If remote fails, try local tool branch
                subprocess.run(["git", "checkout", "tool", "--", f"tool/{tool_name}"], check=True, capture_output=True, cwd=str(project_root))
                success_status = _("python_install_success_status", "Successfully retrieved")
                print(f"{BOLD}{GREEN}{success_status}{RESET} {tool_name} " + _("retrieved_from", "from local '{branch}' branch", branch="tool"))
        except subprocess.CalledProcessError as e:
            fail_msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
            print(f"{BOLD}{RED}{fail_msg}{RESET}: " + _("retrieve_error_msg", "Error retrieving: {error}", error=e))
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

    # 3. Handle pip dependencies if proj/requirements.txt exists
    requirements_path = tool_dir / "core" / "requirements.txt"
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
                # Import get_python_exec from tool/PYTHON/core/utils.py
                python_utils_path = python_tool_dir / "core" / "utils.py"
                if python_utils_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("python_utils_mod", str(python_utils_path))
                    python_utils_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(python_utils_mod)
                    python_exec = python_utils_mod.get_python_exec()
                    
                    # Run pip install using the standalone python
                    result = subprocess.run(
                        [python_exec, "-m", "pip", "install", "-r", str(requirements_path)],
                        capture_output=True, text=True
                    )
                    
                    if result.returncode != 0:
                        error_label = _("error_label", "Error")
                        print(f"{BOLD}{RED}{error_label}{RESET}: " + _("pip_error", "Warning: pip install failed with error:\n{error}", error=result.stderr))
                    else:
                        success_status = _("python_install_success_status", "Successfully installed")
                        print(f"{BOLD}{GREEN}{success_status}{RESET} " + _("pip_success", "pip dependencies for {name} tool.", name=tool_name))
        except Exception as e:
            warning_label = _("warning_label", "Warning")
            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("pip_failed", "Failed to install pip dependencies for {name} tool: {error}", name=tool_name, error=e))

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        msg = _("install_failed", "Failed to install {name} tool", name=tool_name)
        print(f"{BOLD}{RED}{msg}{RESET}: " + _("tool_main_not_found_msg", "Error: {path} not found in tool directory.", path=main_py))
        return

    # 4. Create entry point in bin directory
    bin_dir.mkdir(exist_ok=True)
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
    print(f"然后再运行: PYTHON --py-install 3.10.19")
    print(f"最后再运行: TOOL install {tool_name} (以恢复依赖版本)")
    sys.exit(1)

sys.path.append(str(python_tool_dir))

try:
    from core.utils import get_python_exec
    python_exec = get_python_exec()
except ImportError:
    python_exec = "python3"

# Set up environment
env = os.environ.copy()
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
            os.symlink(main_py, link_path)
        
        success_status = _("python_install_success_status", "Successfully installed")
        print(f"{BOLD}{GREEN}{success_status}{RESET} {tool_name}" + _("shortcut_created", ": shortcut created at {path}", path=link_path))
        
        register_path(bin_dir)
    except OSError as e:
        error_label = _("error_label", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: " + _("shortcut_error", "Error creating shortcut for {name}: {error}", name=tool_name, error=e))

    # 5. Run tool setup if setup.py exists
    setup_py = tool_dir / "setup.py"
    if setup_py.exists():
        action_label = _("label_fetching", "Running")
        print(f"{BLUE}{BOLD}{action_label}{RESET} " + _("running_setup", "setup for {name} tool...", name=tool_name))
        try:
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
    
    if link_path.exists() or link_path.is_symlink():
        try:
            os.remove(link_path)
            print(_("removed_shortcut", "Removed shortcut at {path}", path=link_path))
        except Exception as e:
            print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("remove_shortcut_failed", "Failed to remove shortcut: {error}", error=e))

    try:
        shutil.rmtree(tool_dir)
        print(_("removed_tool_dir", "Removed tool directory at {path}", path=tool_dir))
    except Exception as e:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("remove_tool_dir_failed", "Failed to remove tool directory: {error}", error=e))

    success_status = _("uninstall_success_status", "Successfully uninstalled")
    print(f"{BOLD}{GREEN}{success_status}{RESET} {tool_name}")

def register_path(bin_dir):
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    profiles = []
    if "zsh" in shell: profiles.append(home / ".zshrc")
    elif "bash" in shell:
        profiles.append(home / ".bash_profile")
        profiles.append(home / ".bashrc")
    else: profiles.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
    for profile in profiles:
        if profile.exists():
            with open(profile, 'r') as f: content = f.read()
            if str(bin_dir) not in content:
                with open(profile, 'a') as f: f.write(export_cmd)
                print(_("updated_path", "Updated {profile} with PATH.", profile=profile))

    if str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:" + os.environ["PATH"]

def update_config(key, value):
    project_root = Path(__file__).parent.absolute()
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    config_path = data_dir / "config.json"
    
    if key == "language":
        lang = value.lower()
        if lang != "en":
            audit_path = project_root / "data" / "audit" / "lang" / f"audit_{lang}.json"
            trans_path = project_root / "proj" / "translation" / f"{lang}.json"
            if not audit_path.exists() and not trans_path.exists():
                print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("lang_error_not_found_simple", "Language '{lang}' not found.", lang=lang))
                return
    
    config = {}
    if config_path.exists():
        try:
            with open(config_path, 'r') as f: config = json.load(f)
        except Exception: pass
    
    config[key] = value
    with open(config_path, 'w') as f: json.dump(config, f, indent=2)
    print(_("config_updated", "Global configuration updated: {key} = {value}", key=key, value=value))

def sync_branches():
    """Synchronize core files from 'tool' to 'main', then overwrite 'test' with 'main'."""
    project_root = Path(__file__).parent.absolute()
    core_files = ["main.py", "setup.py", "README.md", ".gitignore", ".gitattributes", "proj", "test", "todo"]
    
    try:
        current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except subprocess.CalledProcessError:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("not_git_repo", "Not a git repository."))
        return
    
    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("sync_uncommitted", "There are uncommitted changes in '{branch}'. Please commit them first.", branch=current_branch))
            return
    except subprocess.CalledProcessError: pass

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
            if cmd[:3] == ["git", "branch", "-D"]:
                subprocess.run(cmd, stderr=subprocess.DEVNULL, cwd=str(project_root))
            elif cmd[:2] == ["git", "commit"]:
                res = subprocess.run(cmd, capture_output=True, text=True, cwd=str(project_root))
                if res.returncode != 0 and "nothing to commit" not in res.stdout:
                    raise subprocess.CalledProcessError(res.returncode, cmd, res.stdout, res.stderr)
            else:
                subprocess.run(cmd, check=True, cwd=str(project_root))
            
            if cmd[:3] == ["git", "checkout", current_branch]:
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
                with open(project_root / ".gitignore", 'w') as f: f.write(gitignore_content)
                subprocess.run(["git", "add", ".gitignore"], cwd=str(project_root), check=True)
                
                for d in ["data", "tmp", "tool", "resource"]:
                    p = project_root / d
                    if p.exists() and p.is_dir():
                        shutil.rmtree(p)
                        subprocess.run(["git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
                    p = project_root / d
                    if p.exists() and p.is_dir():
                        shutil.rmtree(p)
                        subprocess.run(["git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
        except subprocess.CalledProcessError as e:
            print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: Command failed: {' '.join(cmd)}")
            return

    success_status = _("sync_success_status", "Successfully synced")
    print(f"{BOLD}{GREEN}{success_status}{RESET} branches. Ready for testing on 'test'.")

def generate_ai_rule():
    project_root = Path(__file__).parent.absolute()
    registry_path = project_root / "tool.json"
    if not registry_path.exists(): return

    with open(registry_path, 'r') as f: registry = json.load(f)
    tools = registry.get("tools", {})
    installed_tools = [(n, i) for n, i in tools.items() if (project_root / "tool" / n).exists()]
    available_tools = [(n, i) for n, i in tools.items() if not (project_root / "tool" / n).exists()]
            
    lines = []
    lines.append(_("rule_header_main", "--- AI AGENT TOOL RULES ---"))
    lines.append(_("rule_critical_note", "CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations."))
    lines.append("\n" + _("rule_installed_header", "[INSTALLED TOOLS - Use these directly]"))
    for name, info in installed_tools:
        tool_core_dir = project_root / "tool" / name / "core"
        desc = get_translation(str(tool_core_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_core_dir), f"tool_{name}_purpose", info.get('purpose'))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_available_header", "[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]"))
    for name, info in available_tools:
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
    if sys.platform == "darwin":
        try: subprocess.run('pbcopy', input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
        except: pass

def _test_tool_with_args(args):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root if args.tool_name == "root" else project_root / "tool" / args.tool_name
    if not tool_dir.exists(): return
    max_concurrent = 1
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        with open(tool_json_path, 'r') as f:
            data = json.load(f)
            max_concurrent = data.get("test_parallel", 1)
    if args.max != 3: max_concurrent = args.max
    sys.path.append(str(project_root))
    from proj.test_runner import TestRunner
    runner = TestRunner(args.tool_name, project_root)
    if args.list: runner.list_tests()
    else: runner.run_tests(args.range[0] if args.range else None, args.range[1] if args.range else None, max_concurrent, args.timeout)

def _audit_lang(lang_code, force=False):
    project_root = Path(__file__).parent.absolute()
    lang_name = _(f"lang_name_{lang_code}", lang_code)
    sys.path.append(str(project_root))
    from proj.lang.audit import LangAuditor
    from proj.utils import get_rate_color
    if force:
        p = project_root / "data" / "audit" / "lang" / f"audit_{lang_code}.json"
        if p.exists(): p.unlink()
    auditor = LangAuditor(project_root, lang_code)
    msg = _("audit_scanning", "Scanning translation coverage for {lang} ({lang_name})...", lang=lang_code, lang_name=lang_name)
    print(f"{BLUE}{msg}{RESET}", end="", flush=True)
    results, cached = auditor.audit()
    summary = results.get("summary", {})
    print("\r" + " " * 80 + "\r", end="")
    print(_("audit_scanning_done", "Translation audit scan for {lang} ({lang_name}) complete.", lang=lang_code, lang_name=lang_name))
    colors = {"BOLD": BOLD, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW, "RED": RED, "RESET": RESET}
    rk, rr = summary.get("completion_rate_keys", "0%"), summary.get("completion_rate_refs", "0%")
    ck, cr = get_rate_color(rk, colors), get_rate_color(rr, colors)
    print(_("audit_summary_keys", "{rate} of keys support {lang} ({lang_name}) translation ({supported}/{total})", rate=f"{ck}{rk}{RESET}", supported=summary.get("supported_keys"), total=summary.get("total_keys"), lang=lang_code, lang_name=lang_name))
    print(_("audit_summary_refs", "{rate} of references support {lang} ({lang_name}) translation ({supported}/{total})", rate=f"{cr}{rr}{RESET}", supported=summary.get("supported_references"), total=summary.get("total_references"), lang=lang_code, lang_name=lang_name))
    if cached:
        AuditManager(project_root / "data" / "audit" / "lang", component_name="LANG_AUDIT", audit_command=f"TOOL audit-lang {lang_code}").print_cache_warning()

def _list_languages():
    project_root = Path(__file__).parent.absolute()
    sys.path.append(str(project_root))
    from proj.lang.audit import LangAuditor
    from proj.utils import get_rate_color, format_table
    auditor = LangAuditor(project_root)
    audited_langs = auditor.list_audited_languages()
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f: current_lang = json.load(f).get("language", "en")
    rows = [{"code": "en", "name": _("lang_name_en", "English"), "keys": _("lang_default", "default"), "refs": _("lang_default", "default"), "is_current": current_lang == "en"}]
    colors = {"BOLD": BOLD, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW, "RED": RED, "RESET": RESET}
    for lang in audited_langs:
        if lang == "en": continue
        res, _ = LangAuditor(project_root, lang).audit()
        summary = res.get("summary", {})
        rk, rr = summary.get("completion_rate_keys", "0%"), summary.get("completion_rate_refs", "0%")
        ck, cr = get_rate_color(rk, colors), get_rate_color(rr, colors)
        rows.append({"code": lang, "name": _(f"lang_name_{lang}", lang), "keys": f"{ck}{rk}{RESET}", "refs": f"{cr}{rr}{RESET}", "is_current": current_lang == lang})
    headers = [_("lang_table_name", "Language"), _("lang_table_keys", "Key Coverage"), _("lang_table_refs", "Ref Coverage")]
    table_rows = [[f"{r['name']}({r['code']})", r["keys"], r["refs"] + (" *" if r["is_current"] else "")] for r in rows]
    table_str, _ = format_table(headers, table_rows, max_width=80, save_dir="lang")
    print("\n" + _("lang_list_header", "Supported Languages:") + "\n" + table_str)

def main():
    import argparse
    parser = argparse.ArgumentParser(prog="TOOL", description="AITerminalTools manager.")
    subparsers = parser.add_subparsers(dest="command")
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("tool_name")
    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("tool_name")
    uninstall_parser.add_argument("-y", "--yes", action="store_true")
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("tool_name", nargs="?", default="root")
    test_parser.add_argument("--list", action="store_true")
    test_parser.add_argument("--range", nargs=2, type=int)
    test_parser.add_argument("--max", type=int, default=3)
    test_parser.add_argument("--timeout", type=int, default=60)
    audit_parser = subparsers.add_parser("audit-lang")
    audit_parser.add_argument("lang_code")
    audit_parser.add_argument("--force", action="store_true")
    lang_parser = subparsers.add_parser("lang")
    lang_parser.add_argument("--set")
    lang_parser.add_argument("--list", action="store_true")
    subparsers.add_parser("rule")
    subparsers.add_parser("sync")
    if len(sys.argv) < 2:
        parser.print_help()
        return
    args = parser.parse_args()
    if args.command == "install": install_tool(args.tool_name)
    elif args.command == "uninstall": uninstall_tool(args.tool_name, args.yes)
    elif args.command == "test": _test_tool_with_args(args)
    elif args.command == "audit-lang": _audit_lang(args.lang_code, force=args.force)
    elif args.command == "lang":
        if args.set: update_config("language", args.set)
        elif args.list: _list_languages()
    elif args.command == "rule": generate_ai_rule()
    elif args.command == "sync": sync_branches()

if __name__ == "__main__":
    main()
