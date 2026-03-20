import os
import sys
import subprocess
import time
import json
from pathlib import Path
from typing import Optional, Callable


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return _git_bin()

from logic._.config import get_color, get_setting, get_global_config
from logic._.utils import get_cpu_percent
from logic._.utils.turing.models.progress import ProgressTuringMachine
from logic._.utils.turing.logic import TuringStage

def _resolve_tool_name(name: str, project_root: Path) -> str:
    """Resolve a shortcut name (e.g. 'GDS') to the full tool name (e.g. 'GOOGLE.GDS')."""
    tool_dir = project_root / "tool" / name
    if tool_dir.exists() and (tool_dir / "main.py").exists():
        return name
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        with open(registry_path) as f:
            registry = json.load(f)
        for full_name in registry.get("tools", []):
            shortcut = full_name.split(".")[-1] if "." in full_name else full_name
            if shortcut == name:
                return full_name
    return name


def test_tool_with_args(args, project_root: Path, translation_func: Optional[Callable] = None):
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    get_color("BLUE", "\033[34m")
    get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    # 0. Capture current branch to return later
    try:
        start_branch = subprocess.check_output([_git_bin(), "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=str(project_root)).strip()
    except:
        start_branch = "dev"

    # Save persistence directories before any potential branch switch
    from logic.git.persistence import get_persistence_manager
    pm = get_persistence_manager(project_root)
    locker_key = pm.save_tools_persistence()

    try:
        actual_tool_name = "root" if args.tool_name in ["root", "TOOL"] else args.tool_name
        if actual_tool_name != "root":
            actual_tool_name = _resolve_tool_name(actual_tool_name, project_root)
        tool_dir = project_root if actual_tool_name == "root" else project_root / "tool" / actual_tool_name
        if not tool_dir.exists() and actual_tool_name != "root":
            print(f"{BOLD}{RED}Error{RESET}: Tool '{args.tool_name}' not found.")
            return
        
        default_concurrency = get_setting("test_default_concurrency", 3)
        max_concurrent = default_concurrency
        if args.max != 3: 
            max_concurrent = args.max
        elif args.max == 3 and default_concurrency != 3:
            max_concurrent = default_concurrency

        global_cpu_limit = get_global_config("test_cpu_limit", 80.0)
        cpu_timeout = get_global_config("test_cpu_timeout", 30)
        cpu_limit = global_cpu_limit
        if actual_tool_name != "root":
            try:
                tool_config_path = tool_dir / "data" / "config.json"
                if tool_config_path.exists():
                    with open(tool_config_path, 'r') as f:
                        tool_cpu_limit = json.load(f).get("cpu_limit")
                        if tool_cpu_limit is not None: cpu_limit = tool_cpu_limit
            except: pass
        
        def wait_for_cpu_action(stage: TuringStage):
            start_wait_time = time.time()
            while True:
                current_cpu = get_cpu_percent(interval=1.0)
                elapsed_wait_time = time.time() - start_wait_time
                if current_cpu <= cpu_limit:
                    stage.success_status = _("test_cpu_ready", "CPU load is {current_cpu:.1f}% (below limit {cpu_limit:.1f}%)", current_cpu=current_cpu, cpu_limit=cpu_limit)
                    return True
                if elapsed_wait_time > cpu_timeout:
                    stage.fail_status = _("test_cpu_timeout_warn", "CPU load ({current_cpu:.1f}%) still high after {timeout}s. Proceeding with warning.", current_cpu=current_cpu, timeout=cpu_timeout)
                    return True
                stage.active_name = _("test_cpu_waiting", "Waiting for CPU load to drop ({current_cpu:.1f}% > {cpu_limit:.1f}%) ({elapsed_wait_time:.0f}s / {timeout}s)", current_cpu=current_cpu, cpu_limit=cpu_limit, elapsed_wait_time=elapsed_wait_time, timeout=cpu_timeout)
                stage.refresh()
                time.sleep(1)

        current_cpu_at_start = get_cpu_percent(interval=0.1)
        if current_cpu_at_start >= 0.6 * cpu_limit:
            label = _("test_current_cpu_load_label", "Current CPU load: ")
            max_label = _("label_max", "max")
            # Ensure only xx% is bolded, and no extra newline here
            sys.stdout.write(f"{label}{BOLD}{current_cpu_at_start:.1f}%{RESET} ({max_label}: {cpu_limit:.1f}%)\n")
            sys.stdout.flush()
        
        cpu_wait_tm = ProgressTuringMachine(project_root=project_root, tool_name="TOOL", no_warning=args.no_warning) 
        cpu_wait_tm.add_stage(TuringStage(
            name=_("label_cpu_load", "CPU load"),
            action=wait_for_cpu_action,
            active_status=_("test_waiting_for", "Waiting for"),
            success_status=_("label_checked", "Checked"),
            fail_status=_("label_failed_to_check", "Failed to check"),
            bold_part=_("label_waiting_for_cpu_load", "Waiting for CPU load"),
            stealth=True
        ))
        # Use final_newline=False to avoid extra blank line if it's stealthy
        cpu_wait_tm.run(ephemeral=True, final_msg=None, final_newline=False)

        from logic._.test.runner import TestRunner
        if actual_tool_name == "root":
            runner = TestRunner("root", project_root)
            if args.list: runner.list_tests()
            else: runner.run_tests(args.range[0] if args.range else None, args.range[1] if args.range else None, max_concurrent, args.timeout)
        else:
            if not run_installation_test(actual_tool_name, project_root, stay_on_test=True, translation_func=_):
                return
            runner = TestRunner(actual_tool_name, project_root)
            if args.list: runner.list_tests()
            else: runner.run_tests(args.range[0] if args.range else None, args.range[1] if args.range else None, max_concurrent, args.timeout, quiet_if_no_tests=True)
                
        subprocess.run([_git_bin(), "checkout", "-f", start_branch], cwd=str(project_root), capture_output=True)
    finally:
        if locker_key:
            pm.restore(locker_key)

def run_installation_test(tool_name: str, project_root: Path, stay_on_test: bool = False, translation_func: Optional[Callable] = None) -> bool:
    """Run dev sync and then verify installation on test branch."""
    _ = translation_func or (lambda k, d, **kwargs: d.format(**kwargs))
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    from logic.git.persistence import get_persistence_manager
    pm = get_persistence_manager(project_root)
    locker_key = pm.save_tools_persistence()
    
    try:
        start_time = time.time()
        try:
            res = subprocess.run([_git_bin(), "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, cwd=str(project_root))
            current_branch = res.stdout.strip() if res.returncode == 0 else "dev"
        except:
            current_branch = "dev"

        def sync_action():
            from logic._.dev.commands import dev_sync
            with open(os.devnull, 'w') as f:
                from contextlib import redirect_stdout, redirect_stderr
                with redirect_stdout(f), redirect_stderr(f):
                    success = dev_sync(project_root, quiet=True, translation_func=_)
                    if success:
                        subprocess.run([_git_bin(), "checkout", "-f", "test"], cwd=str(project_root), capture_output=True)
                        subprocess.run([_git_bin(), "clean", "-fd", "--exclude=tool/", "--exclude=data/", "--exclude=bin/", "--exclude=logic/config/tool_config_manager.py"], cwd=str(project_root), capture_output=True)
                    return success

        tm_sync = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")
        tm_sync.add_stage(TuringStage(
            name="", action=sync_action, 
            active_status=_("label_syncing_branches", "Syncing branches"),
            success_status=_("label_successfully_synced", "Successfully synced"), 
            success_name=_("label_branches", "branches"), 
            fail_status=_("err_failed_to_sync", "Failed to sync"),
            fail_name=_("label_branches", "branches"),
            bold_part=_("label_syncing_branches", "Syncing branches")
        ))
        
        if not tm_sync.run(ephemeral=True, final_msg=None, final_newline=False):
            print(f"\n{BOLD}{RED}" + _("err_failed_to_sync", "Failed to sync") + f"{RESET} " + _("err_sync_installation_test", "during installation test."))
            return False

        tm_install = ProgressTuringMachine(project_root=project_root, tool_name="TOOL")
        def install_test_action(stage):
            error_details = []
            def _fail(brief, details=None):
                stage.error_brief = brief
                if details:
                    error_details.extend(details) if isinstance(details, list) else error_details.append(details)
                install_test_action.error_msg = "\n".join(error_details) if error_details else brief
                return False

            try:
                subprocess.run([sys.executable, "main.py", "uninstall", tool_name, "-y"], cwd=str(project_root), capture_output=True)
                res = subprocess.run([sys.executable, "main.py", "install", tool_name], cwd=str(project_root), capture_output=True, text=True)
                if res.returncode != 0:
                    brief = f"'TOOL install {tool_name}' exited with code {res.returncode}"
                    extra = []
                    if res.stderr: extra.append(res.stderr.strip())
                    elif res.stdout: extra.append(res.stdout.strip())
                    return _fail(brief, extra)
                
                shortcut_name = tool_name.split('.')[-1] if '.' in tool_name else tool_name
                bin_path = project_root / "bin" / shortcut_name / shortcut_name
                if not bin_path.exists():
                    bin_path = project_root / "bin" / shortcut_name
                if not bin_path.exists():
                    return _fail(f"Shortcut bin/{shortcut_name} not found after install")
                
                res = subprocess.run([str(bin_path), "--help"], capture_output=True, text=True)
                if res.returncode != 0:
                    brief = f"'{shortcut_name} --help' exited with code {res.returncode}"
                    extra = []
                    if res.stderr: extra.append(res.stderr.strip())
                    return _fail(brief, extra)
                return True
            except Exception as e:
                return _fail(f"Unexpected error: {e}")

        tm_install.add_stage(TuringStage(
            name=_("label_installation", "installation"), 
            action=install_test_action, 
            active_status=_("label_testing", "Testing"),
            success_status=_("label_successfully_tested", "Successfully tested"), 
            fail_status=_("label_failed_to_test", "Failed to test"),
            bold_part=_("label_testing_installation", "Testing installation")
        ))
        
        if tm_install.run(ephemeral=True, final_msg=None, final_newline=False):
            duration = time.time() - start_time
            success_label = _("test_install_success", "Successfully installed")
            duration_label = _("label_duration", "Duration")
            print(f"{BOLD}{GREEN}{success_label}{RESET} ({duration_label}: {duration:.2f}s)")
            if not stay_on_test:
                subprocess.run([_git_bin(), "checkout", "-f", current_branch], cwd=str(project_root), capture_output=True)
            return True
        else:
            error_msg = getattr(install_test_action, 'error_msg', 'Unknown error')
            lines = error_msg.split("\n")
            print(f"\n{BOLD}{RED}" + _("label_failed_to_test", "Failed to test") + f"{RESET} " + _("label_installation", "installation") + f". " + _("label_reason", "Reason") + f": {lines[0]}")
            if len(lines) > 1:
                for line in lines[1:]:
                    print(f"  {line}")
            subprocess.run([_git_bin(), "checkout", "-f", current_branch], cwd=str(project_root), capture_output=True)
            return False
    finally:
        if locker_key:
            pm.restore(locker_key)

