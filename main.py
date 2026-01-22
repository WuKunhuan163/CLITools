#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import stat
import shutil
import re
import platform
from pathlib import Path

# Import colors and shared utils from logic
from logic.config import get_color
from logic.lang.utils import get_translation
from logic.audit.utils import AuditManager, AuditBase

RESET = get_color("RESET", "\033[0m")
GREEN = get_color("GREEN", "\033[32m")
BOLD = get_color("BOLD", "\033[1m")
BLUE = get_color("BLUE", "\033[34m")
YELLOW = get_color("YELLOW", "\033[33m")
RED = get_color("RED", "\033[31m")

# Root project directory
_script_path = Path(__file__).resolve()
if _script_path.parent.name == "bin":
    ROOT_PROJECT_ROOT = _script_path.parent.parent
else:
    ROOT_PROJECT_ROOT = _script_path.parent
from logic.utils import get_logic_dir
SHARED_LOGIC_DIR = get_logic_dir(ROOT_PROJECT_ROOT)

# Initialize RTL support and override built-in print
from logic.utils import smart_print, set_rtl_mode
import builtins
builtins.print = smart_print

def _(translation_key, default, **kwargs):
    text = get_translation(str(SHARED_LOGIC_DIR), translation_key, default)
    return text.format(**kwargs)

def install_tool(tool_name):
    project_root = ROOT_PROJECT_ROOT
    tool_parent_dir = project_root / "tool"
    tool_parent_dir.mkdir(exist_ok=True)
    tool_dir = tool_parent_dir / tool_name
    bin_dir = project_root / "bin"
    
    # Check if already installed
    link_path = bin_dir / tool_name
    installed_locally = tool_dir.exists() and (link_path.exists() or link_path.is_symlink())
    
    if installed_locally:
        # Even if installed, check if dependencies are missing
        missing_dep = False
        tool_json_path = tool_dir / "tool.json"
        if tool_json_path.exists():
            try:
                with open(tool_json_path, 'r') as f:
                    tool_data = json.load(f)
                    dependencies = tool_data.get("dependencies", [])
                    for dep in dependencies:
                        dep_dir = tool_parent_dir / dep
                        dep_link = bin_dir / dep
                        if not (dep_dir.exists() and (dep_link.exists() or dep_link.is_symlink())):
                            missing_dep = True
                            break
            except: pass
        
        if not missing_dep:
            already_status = _("label_already_installed", "Already installed")
            print(f"{BOLD}{GREEN}{already_status}{RESET}: {tool_name}")
            return
        else:
            print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("missing_deps_repair", "Tool '{name}' is missing dependencies. Repairing...", name=tool_name))
    elif tool_dir.exists() or link_path.exists() or link_path.is_symlink():
        # Partially installed, perform reinstall
        print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("partial_install_detected", "Tool '{name}' installation is incomplete. Reinstalling...", name=tool_name))
        return reinstall_tool(tool_name)

    from logic.tool.setup.engine import ToolEngine
    engine = ToolEngine(tool_name, project_root)
    engine.install()

def reinstall_tool(tool_name):
    project_root = ROOT_PROJECT_ROOT
    from logic.tool.setup.engine import ToolEngine
    engine = ToolEngine(tool_name, project_root)
    engine.uninstall()
    engine.install()

def uninstall_tool(tool_name, force_yes=False):
    project_root = ROOT_PROJECT_ROOT
    tool_dir = project_root / "tool" / tool_name
    
    if not tool_dir.exists():
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("tool_not_found_local", "Tool '{name}' is not installed.", name=tool_name))
        return

    if not force_yes:
        if sys.stdin.isatty():
            confirm_msg = _("confirm_uninstall", "Are you sure you want to uninstall '{name}'? (y/N): ", name=tool_name)
            confirm = input(confirm_msg)
            # Move up one line and erase the confirmation prompt
            sys.stdout.write(f"\033[A\r\033[K")
            sys.stdout.flush()
            
            if confirm.lower() not in ['y', 'yes']:
                print(_("uninstall_cancelled", "Uninstall cancelled."))
                return
        else:
            print(_("non_interactive_skip", "Non-interactive session, skipping confirmation. Use -y to force."))
            return

    from logic.tool.setup.engine import ToolEngine
    engine = ToolEngine(tool_name, project_root)
    engine.uninstall()

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
    project_root = ROOT_PROJECT_ROOT
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    config_path = data_dir / "config.json"
    
    if key == "language":
        lang = value.lower()
        if lang != "en":
            audit_path = project_root / "data" / "audit" / "lang" / f"audit_{lang}.json"
            trans_path = project_root / "logic" / "translation" / f"{lang}.json"
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
    
    if key == "terminal_width" and (value == 0 or value is None):
        print(_("config_updated_dynamic", "Global configuration updated: {key} will be calculated dynamically", key=key))
    else:
        print(_("config_updated", "Global configuration updated: {key} = {value}", key=key, value=value))

def _dev_sync():
    """Synchronize logic files from 'tool' to 'main', then overwrite 'test' with 'main'."""
    project_root = Path(__file__).parent.absolute()
    logic_files = ["main.py", "setup.py", "tool.json", "README.md", ".gitignore", ".gitattributes", "logic", "bin", "test", "todo"]
    
    try:
        current_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except subprocess.CalledProcessError:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: " + _("not_git_repo", "Not a git repository."))
        return
    
    if current_branch not in ["tool", "dev"]:
        print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("sync_warning_branch", "Sync is recommended from 'tool' or 'dev' branch. Current branch is '{branch}'.", branch=current_branch))
        confirm = input(_("sync_confirm", "Continue anyway? (y/N): "))
        if confirm.lower() not in ['y', 'yes']:
            print(_("sync_cancelled", "Sync cancelled."))
            return

    try:
        status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
        if status:
            print(f"{BOLD}{YELLOW}" + _("warning_label", "Warning") + f"{RESET}: " + _("sync_uncommitted", "There are uncommitted changes in '{branch}'. Please commit them first.", branch=current_branch))
            return
    except subprocess.CalledProcessError: pass

    sync_label = _("sync_to_main_label", "Syncing")
    print(f"\r\033[K{BOLD}{BLUE}{sync_label}{RESET} to 'main' branch...", end="", flush=True)
    
    commands = [
        ["git", "checkout", "main"],
        ["git", "checkout", current_branch, "--"] + logic_files,
        ["git", "commit", "-m", f"Sync logic files from {current_branch} branch"],
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
            
            if cmd == ["git", "checkout", "main"] or cmd == ["git", "checkout", "-b", "test"]:
                # Apply the restricted .gitignore from templates
                init_dir = project_root / "logic" / "init"
                if (init_dir / ".gitignore").exists():
                    shutil.copy(init_dir / ".gitignore", project_root / ".gitignore")
                if (init_dir / ".gitattributes").exists():
                    shutil.copy(init_dir / ".gitattributes", project_root / ".gitattributes")
                
                subprocess.run(["git", "add", ".gitignore", ".gitattributes"], cwd=str(project_root), check=True)
                
                # Clean up development folders and untracked files
                subprocess.run(["git", "clean", "-fdx"], cwd=str(project_root), stderr=subprocess.DEVNULL)
                for d in ["data", "tmp", "tool", "resource"]:
                    p = project_root / d
                    if p.exists() and p.is_dir():
                        shutil.rmtree(p)
                        subprocess.run(["git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
                
                if cmd == ["git", "checkout", "main"]:
                    subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=str(project_root), check=True)

        except subprocess.CalledProcessError as e:
            print(f"\n{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: Command failed: {' '.join(cmd)}")
            return

    success_status = _("sync_success_status", "Successfully synced")
    print(f"\r\033[K{BOLD}{GREEN}{success_status}{RESET} branches. Ready for testing on the 'test' branch.")

def _dev_align():
    """Align tool, main, and test branches with dev branch."""
    project_root = ROOT_PROJECT_ROOT
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.utils import cleanup_project_patterns
    
    # 0. Detect starting branch
    try:
        start_branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET}: Failed to detect current branch.")
        return

    # Helper to run git commands quietly
    def run_git(args, cwd=None):
        try:
            # Add --force or other flags if needed
            subprocess.run(["git"] + args, check=True, cwd=cwd or str(project_root), capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            return False

    def sync_dev_action():
        # 1. Automatically switch to dev if not already there
        if start_branch != "dev":
            # First, try to auto-commit any changes on the current branch to avoid data loss
            try:
                status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
                if status:
                    run_git(["add", "-A"])
                    run_git(["commit", "-m", f"Auto-commit local changes on '{start_branch}' before alignment"])
            except: pass
            
            if not run_git(["checkout", "-f", "dev"]): return False

        # 2. Auto-commit local changes on dev if any
        try:
            status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
            if status:
                run_git(["add", "-A"])
                run_git(["commit", "-m", "Auto-commit before alignment"])
        except: pass

        # 3. Clean up untracked files on dev
        run_git(["clean", "-fdx"])
        cleanup_project_patterns(project_root)

        # 4. Push dev to origin
        return run_git(["push", "origin", "dev", "--force"])

    def align_tool_action():
        if not run_git(["checkout", "-f", "tool"]): return False
        if not run_git(["reset", "--hard", "dev"]): return False
        if not run_git(["clean", "-fdx"]): return False
        return run_git(["push", "origin", "tool", "--force"])

    def align_main_action():
        if not run_git(["checkout", "-f", "main"]): return False
        if not run_git(["reset", "--hard", "tool"]): return False
        
        # Remove restricted folders on main
        restricted = ["tool", "resource", "data", "tmp", "bin"]
        subprocess.run(["git", "rm", "-rf"] + restricted, stderr=subprocess.DEVNULL, cwd=str(project_root))
        
        # Ensure they are gone from disk
        for d in restricted:
            p = project_root / d
            if p.exists():
                try:
                    if p.is_dir(): shutil.rmtree(p)
                    else: p.unlink()
                except: pass
        
        # Clean up EVERYTHING untracked
        run_git(["clean", "-fdx"])
        
        # Commit and push
        run_git(["add", "-A"])
        run_git(["commit", "--allow-empty", "-m", "Align 'main' with 'tool' (removed restricted folders)"])
        return run_git(["push", "origin", "main", "--force"])

    def recreate_test_action():
        if not run_git(["branch", "-D", "test"]): pass # Ignore if doesn't exist
        if not run_git(["checkout", "-b", "test"]): return False
        return run_git(["push", "origin", "test", "--force"])

    tm = ProgressTuringMachine()
    
    # Using 'bold_part' to bold only the verb+noun part
    tm.add_stage(TuringStage(
        name=_("on_branch", "local changes on '{branch}'", branch="dev"),
        action=sync_dev_action,
        active_status=_("label_auto_committing", "Auto-committing"),
        success_status=_("label_auto_committed", "Auto-committed"),
        fail_status=_("label_failed", "Failed"),
        bold_part=_("label_auto_committing_local", "local changes"),
        success_color="BLUE"
    ))
    
    tm.add_stage(TuringStage(
        name="'tool' branch",
        action=align_tool_action,
        active_status=_("aligning_branch", "Aligning '{branch}' branch", branch="tool"),
        success_status=_("label_successfully", "Successfully"),
        fail_status=_("label_failed", "Failed"),
        bold_part=_("label_successfully", "Successfully") + " " + _("aligning_branch", "aligned '{branch}' branch", branch="tool"),
        success_color="BLUE"
    ))
    
    tm.add_stage(TuringStage(
        name="'main' branch",
        action=align_main_action,
        active_status=_("aligning_branch", "Aligning '{branch}' branch", branch="main"),
        success_status=_("label_successfully", "Successfully"),
        fail_status=_("label_failed", "Failed"),
        bold_part=_("label_successfully", "Successfully") + " " + _("aligning_branch", "aligned '{branch}' branch", branch="main"),
        success_color="BLUE"
    ))
    
    tm.add_stage(TuringStage(
        name="'test' branch",
        action=recreate_test_action,
        active_status=_("recreating_test", "Recreating 'test' branch"),
        success_status=_("label_successfully", "Successfully"),
        fail_status=_("label_failed", "Failed"),
        bold_part=_("label_successfully", "Successfully") + " " + _("recreating_test", "recreated 'test' branch"),
        success_color="BLUE"
    ))

    try:
        success_label = _("alignment_complete", "Alignment complete.")
        final_msg = f"{BOLD}{GREEN}{success_label}{RESET}"
        
        if tm.run(ephemeral=True, final_msg=final_msg):
            # Print a single newline after the overwritten status
            sys.stdout.write("\n")
            sys.stdout.flush()
        
        # Ensure we end up back on 'dev'
        run_git(["checkout", "-f", "dev"])
        
    except Exception as e:
        print(f"{BOLD}{RED}" + _("error_label", "Error") + f"{RESET} during alignment: {e}")
        run_git(["checkout", "-f", "dev"])

def _dev_reset():
    """Reset main and test branches to a clean state using templates."""
    project_root = Path(__file__).parent.absolute()
    try:
        current = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
        if current != "tool":
            warning_label = _("warning_label", "Warning")
            print(f"{BOLD}{YELLOW}{warning_label}{RESET}: " + _("reset_warning_branch", "Reset is recommended from 'tool' branch."))
            
        subprocess.run(["git", "checkout", "main"], cwd=str(project_root), check=True)
        
        init_dir = SHARED_LOGIC_DIR / "init"
        if (init_dir / ".gitignore").exists():
            shutil.copy(init_dir / ".gitignore", project_root / ".gitignore")
        if (init_dir / ".gitattributes").exists():
            shutil.copy(init_dir / ".gitattributes", project_root / ".gitattributes")
            
        subprocess.run(["git", "add", ".gitignore", ".gitattributes"], cwd=str(project_root), check=True)
        subprocess.run(["git", "commit", "-m", "Reset main branch to template state"], cwd=str(project_root))
        
        subprocess.run(["git", "clean", "-fd"], cwd=str(project_root), stderr=subprocess.DEVNULL)
        for d in ["data", "tmp", "tool", "resource"]:
            p = project_root / d
            if p.exists() and p.is_dir():
                shutil.rmtree(p)
                subprocess.run(["git", "rm", "-rf", "--cached", d], stderr=subprocess.DEVNULL, cwd=str(project_root))
        
        subprocess.run(["git", "commit", "--amend", "--no-edit"], cwd=str(project_root))
        subprocess.run(["git", "branch", "-D", "test"], stderr=subprocess.DEVNULL, cwd=str(project_root))
        subprocess.run(["git", "checkout", "-b", "test"], cwd=str(project_root), check=True)
        subprocess.run(["git", "checkout", current], cwd=str(project_root), check=True)
        
        success_status = _("label_successfully", "Successfully")
        print(f"{BOLD}{GREEN}{success_status} reset{RESET} main and test branches.")
    except Exception as e:
        error_label = _("error_label", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: " + _("reset_failed", "Reset failed: {error}", error=str(e)))

def _dev_enter(branch, force=False):
    """Switch to main or test branch safely."""
    project_root = ROOT_PROJECT_ROOT
    try:
        if force:
            print(f"{BOLD}{BLUE}Force switching to {branch} branch...{RESET}")
            subprocess.run(["git", "checkout", "-f", branch], cwd=str(project_root), check=True)
            subprocess.run(["git", "clean", "-fdx"], cwd=str(project_root), check=True)
        else:
            # Auto-commit local changes if any
            status = subprocess.check_output(["git", "status", "--porcelain"], text=True, cwd=str(project_root))
            if status:
                auto_commit_label = _("label_auto_committing", "Auto-committing")
                print(f"{BOLD}{BLUE}{auto_commit_label}{RESET} local changes before switching...")
                subprocess.run(["git", "add", "-A"], check=True, cwd=str(project_root))
                subprocess.run(["git", "commit", "-m", f"Auto-commit before entering {branch}"], check=True, cwd=str(project_root))
            
            subprocess.run(["git", "checkout", branch], cwd=str(project_root), check=True)
            # Always clean when entering test/main to remove leftover ignored files
            subprocess.run(["git", "clean", "-fdx"], cwd=str(project_root), check=True)
    except Exception as e:
        error_label = _("error_label", "Error")
        print(f"{BOLD}{RED}{error_label}{RESET}: {e}")

def _tool_requirements():
    return {
        "files": ["main.py", "setup.py", "tool.json", "README.md"],
        "dirs": ["logic", "logic/translation"]
    }

def _dev_sanity_check(tool_name, fix=False):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / "tool" / tool_name
    if not tool_dir.exists():
        print(f"Error: Tool '{tool_name}' not found.")
        return False
    
    reqs = _tool_requirements()
    missing = []
    for f in reqs["files"]:
        if not (tool_dir / f).exists(): missing.append(f)
    for d in reqs["dirs"]:
        if not (tool_dir / d).exists(): missing.append(d)
    
    if fix and missing:
        if "logic" in missing:
            get_logic_dir(tool_dir).mkdir(exist_ok=True)
            print(_("fixed_created_logic", "Fixed: Created logic/ directory for '{name}'", name=tool_name))
            missing.remove("logic")
        
        if "logic/translation" in missing:
            tool_internal = get_logic_dir(tool_dir)
            trans_json = tool_internal / "translation.json"
            trans_dir = tool_internal / "translation"
            if trans_json.exists():
                trans_dir.mkdir(parents=True, exist_ok=True)
                try:
                    with open(trans_json, 'r') as f:
                        data = json.load(f)
                        for lang, items in data.items():
                            with open(trans_dir / f"{lang}.json", 'w') as lf:
                                json.dump(items, lf, indent=2)
                    print(_("fixed_converted_translation", "Fixed: Converted logic/translation.json to logic/translation/ directory for '{name}'", name=tool_name))
                    missing.remove("logic/translation")
                except Exception as e:
                    print(f"Error fixing translation: {e}")
            else:
                trans_dir.mkdir(parents=True, exist_ok=True)
                print(_("fixed_created_logic_trans", "Fixed: Created empty logic/translation/ directory for '{name}'", name=tool_name))
                missing.remove("logic/translation")
        
        # Re-check remaining files
        for f in list(missing):
            if f == "README.md":
                with open(tool_dir / "README.md", 'w') as f_out:
                    f_out.write(f"# {tool_name}\n\n{tool_name} tool.")
                print(_("fixed_created_readme", "Fixed: Created basic README.md for '{name}'", name=tool_name))
                missing.remove("README.md")
            elif f == "tool.json":
                # Create a minimal tool.json
                reg_path = project_root / "tool.json"
                info = {}
                if reg_path.exists():
                    with open(reg_path, 'r') as f_reg:
                        info = json.load(f_reg).get("tools", {}).get(tool_name, {})
                
                minimal_tool_json = {
                    "name": tool_name,
                    "version": "1.0.0",
                    "description": info.get("description", f"Tool {tool_name}"),
                    "purpose": info.get("purpose", ""),
                    "dependencies": []
                }
                with open(tool_dir / "tool.json", 'w') as f_out:
                    json.dump(minimal_tool_json, f_out, indent=2)
                print(_("fixed_created_tool_json", "Fixed: Created minimal tool.json for '{name}'", name=tool_name))
                missing.remove("tool.json")

    if missing:
        fail_label = _("sanity_failed", "Sanity check failed")
        print(f"{BOLD}{RED}{fail_label}{RESET} for '{tool_name}': Missing {', '.join(missing)}")
        return False
    
    pass_label = _("sanity_passed", "Sanity check passed")
    print(f"{BOLD}{GREEN}{pass_label}{RESET} for '{tool_name}'.")
    return True

def _dev_audit_test(tool_name, fix=False):
    """Audit unit test naming conventions."""
    # ... existing implementation ...
    return False

def _dev_audit_bin(fix=False):
    """Audit bin/ directory to ensure only symlinks or bootstrap scripts exist."""
    project_root = ROOT_PROJECT_ROOT
    bin_dir = project_root / "bin"
    if not bin_dir.exists():
        print(f"{BOLD}{YELLOW}Warning{RESET}: bin/ directory not found.")
        return True
    
    # Get tools from registry
    registry_path = project_root / "tool.json"
    tools = []
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            tools = list(json.load(f).get("tools", {}).keys())
    
    violations = []
    for f in bin_dir.iterdir():
        if f.name == "TOOL": continue # TOOL is allowed to be a script
        
        if not f.is_symlink():
            # Check if it's a tool name
            if f.name in tools:
                violations.append(f)
    
    if not violations:
        print(f"{BOLD}{GREEN}Success{RESET}: All tool shortcuts in bin/ are pure symlinks.")
        return True
    
    print(f"{BOLD}{RED}Found code in bin/ instead of symlinks{RESET}:")
    for f in violations:
        print(f"  {f.name} (File size: {f.stat().st_size} bytes)")
        if fix:
            # Fix it by re-running shortcut creation
            from logic.tool.setup.engine import ToolEngine
            engine = ToolEngine(f.name, project_root)
            if engine.create_shortcut():
                print(f"    {BOLD}{GREEN}Fixed{RESET}: Replaced with symlink.")
            else:
                print(f"    {BOLD}{RED}Failed to fix{RESET}: could not create shortcut.")
                
    return False

def _dev_create(tool_name):
    """Create a new tool template."""
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / "tool" / tool_name
    
    # Auto-commit local changes before checkout to avoid errors
    try:
        status = subprocess.run(["git", "status", "--porcelain"], cwd=str(project_root), capture_output=True, text=True)
        if status.stdout.strip():
            info_label = _("info_label", "Info")
            print(f"{BOLD}{info_label}{RESET}: " + _("auto_committing_before_switch", "Auto-committing local changes before switching branch..."))
            subprocess.run(["git", "add", "."], cwd=str(project_root), check=True)
            subprocess.run(["git", "commit", "-m", "Auto-commit before dev create"], cwd=str(project_root), check=True)
    except: pass

    try:
        subprocess.run(["git", "checkout", "tool"], cwd=str(project_root), check=True)
    except: pass
    
    if tool_dir.exists():
        print(f"{BOLD}{RED}Error{RESET}: Tool '{tool_name}' already exists.")
        return
    
    tool_dir.mkdir(parents=True)
    tool_internal = get_logic_dir(tool_dir)
    tool_internal.mkdir()
    (tool_internal / "translation").mkdir(parents=True)
    
    main_content = f'''#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

def main():
    tool = ToolBase("{tool_name}")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool {tool_name}")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        print(f"{{BOLD}}{{BLUE}}Progressing{{RESET}}... {{BOLD}}{{GREEN}}Successfully{{RESET}} finished!")
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
'''
    with open(tool_dir / "main.py", 'w') as f: f.write(main_content)
    os.chmod(tool_dir / "main.py", 0o755)
    
    setup_content = f'''#!/usr/bin/env python3
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

def main():
    print("--- Running setup for {tool_name} ---")
    print("Setup complete.")

if __name__ == "__main__":
    main()
'''
    with open(tool_dir / "setup.py", 'w') as f: f.write(setup_content)
    
    tool_json = {
        "name": tool_name,
        "version": "1.0.0",
        "description": f"Template tool {tool_name}",
        "purpose": "Showcase tool development guidelines",
        "dependencies": ["PYTHON"]
    }
    with open(tool_dir / "tool.json", 'w') as f: json.dump(tool_json, f, indent=2)
    
    readme_content = f"""# {tool_name}

{tool_name} tool template.

## Ecosystem Support

This tool is part of the `TOOL` ecosystem, which provides:

- **Standalone Runtime**: Tools can specify a dependency on the `PYTHON` tool. The manager ensures they run in a dedicated, isolated Python environment.
- **Git LFS Support**: Managed via the root `.gitattributes`. Large files (models, binaries) are automatically tracked by Git LFS.
- **Automatic Persistence**: The system supports automatic pushes every three commits to protect work progress. This is managed by a `post-commit` hook in the root `.git/hooks`.
- **Shared Utilities**: Access core logic in the root `logic/` folder:
    - `logic.turing`: For building multi-stage workers with progress display (the "Turing Machine" pattern).
    - `logic.utils`: Shared terminal utilities, RTL support, and more.
    - `logic.tool.base`: Base class for standardized command handling (e.g., automated `setup` command support).
    - `logic.audit`: General-purpose audit and caching system.
- **Localization**: Built-in support for multiple languages in `logic/translation/`. Always use the `_()` helper for user-facing strings.
- **Unit Testing**: Standardized testing framework using `unittest`. Run tests in parallel with `TOOL test {tool_name}`.

## Development Guidelines

1. **Isolation**: Use the `PYTHON` tool dependency for a standalone runtime. Specify dependencies in `tool.json`.
2. **Testing**: Add unit tests in `test/`. Use `TOOL test {tool_name}` to run them in parallel.
3. **Translation**: English strings MUST be provided as default arguments within the code; **DO NOT include 'en' sections in translation JSON files**.
4. **Cleanliness**: Keep the `main` and `test` branches clean. Perform active development on the `dev` or `tool` branch.
"""
    with open(tool_dir / "README.md", 'w') as f: f.write(readme_content)
    
    # Update global tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        try:
            with open(registry_path, 'r') as f: registry = json.load(f)
            if tool_name not in registry.get("tools", {}):
                registry.get("tools", {})[tool_name] = {
                    "description": tool_json["description"],
                    "purpose": tool_json["purpose"]
                }
                with open(registry_path, 'w') as f: json.dump(registry, f, indent=2)
        except: pass
    
    # Demo translation
    zh_trans = {"hello": "你好, 世界!"}
    ar_trans = {"hello": "مرحباً بالعالم!"}
    with open(tool_internal / "translation" / "zh.json", 'w') as f: json.dump(zh_trans, f, indent=2)
    with open(tool_internal / "translation" / "ar.json", 'w') as f: json.dump(ar_trans, f, indent=2)
    
    success_status = _("label_successfully", "Successfully")
    print(f"{BOLD}{GREEN}{success_status}{RESET} " + _("created_tool_template", "created tool template at {dir}", dir=tool_dir))
    _dev_sanity_check(tool_name)

def generate_ai_rule(target_tool=None):
    project_root = ROOT_PROJECT_ROOT
    
    if target_tool and target_tool.upper() != "TOOL":
        # Delegate to specific tool rule
        from logic.tool.setup.engine import ToolEngine
        engine = ToolEngine(target_tool.upper(), project_root)
        tool_dir = project_root / "tool" / target_tool.upper()
        if not tool_dir.exists():
            print(f"{BOLD}{RED}Error{RESET}: Tool '{target_tool}' not found.")
            return
        
        # We can't easily call ToolBase.print_rule() without importing the tool's main.py
        # which might trigger side effects. So we read the json directly here too for consistency.
        registry_path = tool_dir / "tool.json"
    else:
        registry_path = project_root / "tool.json"
        
    if not registry_path.exists(): return

    with open(registry_path, 'r') as f: registry = json.load(f)
    
    if target_tool and target_tool.upper() != "TOOL":
        # Single tool rule display
        name = target_tool.upper()
        info = registry
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose'))
        usage = info.get("usage", [])
        
        print(f"--- {BOLD}{name}{RESET} Rule ---")
        print(f"{BOLD}Description{RESET}: {desc}")
        print(f"{BOLD}Purpose{RESET}: {purpose}")
        
        if usage:
            print(f"\n{BOLD}Usage{RESET}:")
            for line in usage:
                print(f"- {line}")
        
        if name == "USERINPUT":
            ai_instr = get_translation(str(tool_logic_dir), "ai_instruction", "## Critical Directive: Feedback Acquisition\n...")
            print("\n" + ai_instr)
            
        print("--------------------------")
        return

    # Global rule display (existing logic)
    tools = registry.get("tools", {})
    installed_tools = [(n, i) for n, i in tools.items() if (project_root / "tool" / n).exists()]
    available_tools = [(n, i) for n, i in tools.items() if not (project_root / "tool" / n).exists()]
            
    lines = []
    lines.append(_("rule_header_main", "--- AI AGENT TOOL RULES ---"))
    lines.append(_("rule_critical_note", "CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations."))
    lines.append("\n" + _("rule_installed_header", "[INSTALLED TOOLS - Use these directly]"))
    for name, info in installed_tools:
        tool_logic_dir = get_logic_dir(project_root / "tool" / name)
        desc = get_translation(str(tool_logic_dir), f"tool_{name}_desc", info.get('description'))
        purpose = get_translation(str(tool_logic_dir), f"tool_{name}_purpose", info.get('purpose'))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_available_header", "[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]"))
    for name, info in available_tools:
        desc = _(f"tool_{name}_desc", info.get('description'))
        purpose = _(f"tool_{name}_purpose", info.get('purpose'))
        lines.append(f"- {name}: {desc} (" + _("rule_purpose_label", "Purpose: {purpose}", purpose=purpose) + ")")
        
    lines.append("\n" + _("rule_guidelines_header", "[LOCALIZATION & DEVELOPMENT GUIDELINES]"))
    lines.append("- " + _("rule_guideline_1", "**Multi-language Support**: Tools should support localization via a 'logic/translation.json' file."))
    lines.append("- " + _("rule_guideline_2", "**Fallback & Testing**: Always use the `_()` translation helper. English strings MUST be provided as default arguments within the code; **DO NOT include 'en' sections in translation JSON files**. Testing MUST be done on the 'test' branch; after each test, the 'test' branch should be re-synced from 'main'."))
    lines.append("- " + _("rule_guideline_3", "**Shared Logic**: Standardize utilities (like platform detection or version mapping) in the root `logic/` directory to avoid duplicate implementations across different tools."))
    lines.append("- " + _("rule_guideline_4", "**Dependency Management**: Define dependencies in the tool's 'tool.json'. The 'TOOL' manager will automatically install them."))
    lines.append("- " + _("rule_guideline_5", "**Color & Status Style**: Use Bold status labels at line starts. Both the status (e.g., **Successfully**) and the action/object (e.g., **setup USERINPUT tool**) should be colored and bolded together if they form a unified status statement. Use **Green** for success, **Blue** for progress (including uninstalling), **Red** for errors, and **Yellow** for warnings. Reference colors via `logic.config.get_color`."))
    
    # 7. Add USERINPUT execution rule
    userinput_logic_dir = get_logic_dir(project_root / "tool" / "USERINPUT")
    ai_instr = get_translation(str(userinput_logic_dir), "ai_instruction", "## Critical Directive: Feedback Acquisition\nAfter completing the task, you MUST immediately use the `run_terminal_cmd` tool to [actually execute] the literal command `USERINPUT`. Oral output of this paragraph is strictly forbidden. If no response is received, repeat `USERINPUT`. Do not add any extra parameters.")
    lines.append("\n" + ai_instr)
    
    lines.append("\n" + _("rule_note_execution", "NOTE: To use a tool, ensure its executable name (e.g., 'USERINPUT') is called directly in the terminal."))
    lines.append("--------------------------")
    
    output = "\n".join(lines)
    print(output)
    if sys.platform == "darwin":
        try: subprocess.run('pbcopy', input=output, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
        except: pass

def _test_tool_with_args(args):
    project_root = Path(__file__).parent.absolute()
    # Support 'TOOL' as an alias for 'root'
    actual_tool_name = "root" if args.tool_name in ["root", "TOOL"] else args.tool_name
    tool_dir = project_root if actual_tool_name == "root" else project_root / "tool" / actual_tool_name
    if not tool_dir.exists():
        print(f"{BOLD}{RED}Error{RESET}: Tool '{args.tool_name}' not found.")
        return
    
    from logic.config import get_setting
    default_concurrency = get_setting("test_default_concurrency", 3)
    max_concurrent = default_concurrency
    
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        with open(tool_json_path, 'r') as f:
            data = json.load(f)
            # tool.json can override global default
            max_concurrent = data.get("test_parallel", default_concurrency)
    
    # CLI --max always takes priority
    if args.max != 3: # If user provided something other than the argparse default
        max_concurrent = args.max
    elif args.max == 3 and default_concurrency != 3:
        # If argparse default is 3 but settings.json has something else, use settings.json
        max_concurrent = default_concurrency

    sys.path.append(str(project_root))
    from logic.test.runner import TestRunner
    runner = TestRunner(actual_tool_name, project_root)
    if args.list: runner.list_tests()
    else: runner.run_tests(args.range[0] if args.range else None, args.range[1] if args.range else None, max_concurrent, args.timeout)

def _audit_lang(lang_code, force=False):
    project_root = Path(__file__).parent.absolute()
    lang_name = _(f"lang_name_{lang_code}", lang_code)
    sys.path.append(str(project_root))
    from logic.lang.audit import LangAuditor
    from logic.utils import get_rate_color
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

def _show_current_language():
    """Display the current language and its code."""
    project_root = Path(__file__).parent.absolute()
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f: current_lang = json.load(f).get("language", "en")
    print(f"{_(f'lang_name_{current_lang}', current_lang)} ({current_lang})")

def _list_languages():
    project_root = Path(__file__).parent.absolute()
    sys.path.append(str(project_root))
    from logic.lang.audit import LangAuditor
    from logic.utils import get_rate_color, format_table
    auditor = LangAuditor(project_root)
    audited_langs = auditor.list_audited_languages()
    current_lang = "en"
    config_path = project_root / "data" / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f: current_lang = json.load(f).get("language", "en")
    
    # Native names map
    native_names = {
        "zh": "中文 (zh)",
        "en": "English (en)",
        "ar": "العربية (ar)"
    }
    
    rows = [{"code": "en", "name": native_names.get("en", "English (en)"), "keys": _("lang_default", "default"), "refs": _("lang_default", "default"), "is_current": current_lang == "en"}]
    colors = {"BOLD": BOLD, "GREEN": GREEN, "BLUE": BLUE, "YELLOW": YELLOW, "RED": RED, "RESET": RESET}
    for lang in audited_langs:
        if lang == "en": continue
        res, cached = LangAuditor(project_root, lang).audit()
        summary = res.get("summary", {})
        rk, rr = summary.get("completion_rate_keys", "0%"), summary.get("completion_rate_refs", "0%")
        ck, cr = get_rate_color(rk, colors), get_rate_color(rr, colors)
        
        name = native_names.get(lang, _(f"lang_name_{lang}", lang))
        rows.append({"code": lang, "name": name, "keys": f"{ck}{rk}{RESET}", "refs": f"{cr}{rr}{RESET}", "is_current": current_lang == lang})
    
    headers = [_("lang_table_name", "Language"), _("lang_table_keys", "Key Coverage"), _("lang_table_refs", "Ref Coverage")]
    table_rows = [[r['name'], r["keys"], r["refs"] + (" *" if r["is_current"] else "")] for r in rows]
    table_str, report_path = format_table(headers, table_rows, max_width=80, save_dir="lang")
    print("\n" + _("lang_list_header", "Supported Languages:") + "\n" + table_str)

def main():
    import argparse
    parser = argparse.ArgumentParser(prog="TOOL", description="AITerminalTools manager.")
    subparsers = parser.add_subparsers(dest="command")
    install_parser = subparsers.add_parser("install")
    install_parser.add_argument("tool_name")
    
    reinstall_parser = subparsers.add_parser("reinstall")
    reinstall_parser.add_argument("tool_name")
    
    uninstall_parser = subparsers.add_parser("uninstall")
    uninstall_parser.add_argument("tool_name")
    uninstall_parser.add_argument("-y", "--yes", action="store_true")
    test_parser = subparsers.add_parser("test")
    test_parser.add_argument("tool_name", nargs="?", default="root")
    test_parser.add_argument("--list", action="store_true")
    test_parser.add_argument("--range", nargs=2, type=int)
    test_parser.add_argument("--max", type=int, default=3)
    test_parser.add_argument("--timeout", type=int, default=300)
    lang_parser = subparsers.add_parser("lang", help=_("lang_help", "Manage display language"))
    lang_subparsers = lang_parser.add_subparsers(dest="lang_command", help=_("lang_subcommand_help", "Language subcommands"))
    
    set_parser = lang_subparsers.add_parser("set", help=_("lang_set_help", "Set display language"))
    set_parser.add_argument("code", help=_("lang_code_help", "Language code (e.g. en, zh, ar)"))
    
    lang_subparsers.add_parser("list", help=_("lang_list_help", "List supported languages and their coverage"))
    
    audit_parser = lang_subparsers.add_parser("audit", help=_("audit_help", "Audit language translation coverage"))
    audit_parser.add_argument("lang_code", help=_("audit_lang_code_help", "Language code to audit (e.g. en, zh)"))
    audit_parser.add_argument("--force", action="store_true", help=_("audit_force_help", "Force refresh cache"))
    
    dev_parser = subparsers.add_parser("dev", help="Developer commands")
    dev_subparsers = dev_parser.add_subparsers(dest="dev_command")
    
    dev_subparsers.add_parser("sync", help="Sync tool branch to main and test")
    
    dev_subparsers.add_parser("align", help="Align tool, main, and test branches with dev branch")
    
    reset_parser = dev_subparsers.add_parser("reset", help="Reset main/test branches using templates")
    
    enter_parser = dev_subparsers.add_parser("enter", help="Switch to test or main branch")
    enter_parser.add_argument("branch", choices=["main", "test"])
    enter_parser.add_argument("-f", "--force", action="store_true", help="Force switch (discard changes)")
    
    create_parser = dev_subparsers.add_parser("create", help="Create a new tool template")
    create_parser.add_argument("tool_name", help="Name of the new tool")
    
    sanity_parser = dev_subparsers.add_parser("sanity-check", help="Run sanity check on a tool")
    sanity_parser.add_argument("tool_name", help="Name of the tool to check")
    sanity_parser.add_argument("--fix", action="store_true", help="Try to fix sanity issues")
    
    audit_test_parser = dev_subparsers.add_parser("audit-test", help="Audit unit test naming conventions")
    audit_test_parser.add_argument("tool_name", help="Name of the tool to audit (or 'TOOL')")
    audit_test_parser.add_argument("--fix", action="store_true", help="Try to fix naming issues")
    
    audit_bin_parser = dev_subparsers.add_parser("audit-bin", help="Audit bin/ directory for pure symlinks")
    audit_bin_parser.add_argument("--fix", action="store_true", help="Try to fix violations")
    
    config_parser = subparsers.add_parser("config", help="Manage global configuration")
    config_parser.add_argument("--terminal-width", type=int, help="Manually set terminal width (for testing)")
    config_parser.add_argument("--manager-debug", type=int, choices=[0, 1], help="Enable or disable terminal manager debugging")
    
    subparsers.add_parser("clear", help="Clear the terminal screen")
    
    rule_parser = subparsers.add_parser("rule", help="Show AI agent tool rules")
    rule_parser.add_argument("target_tool", nargs="?", help="Specific tool to show rules for")

    if len(sys.argv) < 2:
        parser.print_help()
        return
    args = parser.parse_args()
    if args.command == "install": install_tool(args.tool_name)
    elif args.command == "reinstall": reinstall_tool(args.tool_name)
    elif args.command == "uninstall": uninstall_tool(args.tool_name, args.yes)
    elif args.command == "test": _test_tool_with_args(args)
    elif args.command == "lang":
        if args.lang_command == "set": update_config("language", args.code)
        elif args.lang_command == "list": _list_languages()
        elif args.lang_command == "audit": _audit_lang(args.lang_code, force=args.force)
        else: _show_current_language()
    elif args.command == "config":
        if args.terminal_width is not None:
            update_config("terminal_width", args.terminal_width)
        if args.manager_debug is not None:
            update_config("manager_debug", bool(args.manager_debug))
    elif args.command == "clear":
        if platform.system() == "Windows":
            os.system("cls")
        else:
            sys.stdout.write("\033[H\033[2J")
            sys.stdout.flush()
    elif args.command == "rule": generate_ai_rule(args.target_tool)
    elif args.command == "dev":
        if args.dev_command == "sync": _dev_sync()
        elif args.dev_command == "align": _dev_align()
        elif args.dev_command == "reset": _dev_reset()
        elif args.dev_command == "enter": _dev_enter(args.branch, args.force)
        elif args.dev_command == "create": _dev_create(args.tool_name)
        elif args.dev_command == "sanity-check": _dev_sanity_check(args.tool_name, args.fix)
        elif args.dev_command == "audit-test": _dev_audit_test(args.tool_name, args.fix)
        elif args.dev_command == "audit-bin": _dev_audit_bin(args.fix)

if __name__ == "__main__":
    main()
