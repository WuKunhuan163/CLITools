#!/usr/bin/env python3 -u
import os
import sys
import argparse
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.interface.tool import ToolBase
from logic.interface.config import get_color


def main():
    os.environ.pop("GCS_CDP_ENABLED", None)
    if "--no-warning" not in sys.argv:
        sys.argv.append("--no-warning")

    # PERFORMANCE OPTIMIZATION: Force IPv4 for Google API requests.
    import socket
    try:
        import urllib3.util.connection as urllib3_cn
        urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
    except Exception:
        pass

    tool = ToolBase("GOOGLE.GCS")
    
    parser = argparse.ArgumentParser(description="Google Drive Remote Controller (GCS)", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # Bash-like subcommands (direct user commands)
    recognized = ["ls", "cat", "cd", "pwd", "upload", "read", "grep", "linter", "edit", "venv", "bg", "setup", "config", "install", "uninstall", "rule", "skills", "-h", "--help", "help"]
    
    ls_parser = subparsers.add_parser("ls", help="List files in a Google Drive folder")
    ls_parser.add_argument("path", nargs="?", default=None, help="Remote path (~ = root, @ = env, e.g. ~/tmp)")
    ls_parser.add_argument("-l", action="store_true", help="Long format listing (shows IDs and types)")
    ls_parser.add_argument("--force", action="store_true", help="Bypass API cache, list via remote shell")
    
    cd_parser = subparsers.add_parser("cd", help="Change remote working directory")
    cd_parser.add_argument("path", nargs="?", default="~", help="Remote path (~ = root, @ = env, or relative)")
    cd_parser.add_argument("--force", action="store_true", help="Bypass API cache, verify via remote shell")
    
    upload_parser = subparsers.add_parser("upload", help="Upload a local file to remote Google Drive")
    upload_parser.add_argument("local_path", help="Local file path to upload")
    upload_parser.add_argument("remote_path", nargs="?", default=None, help="Remote destination (~ = root, @ = env). Default: current directory")
    upload_parser.add_argument("--force-base64", action="store_true", help="Force base64 upload via Colab (max 2MB)")

    subparsers.add_parser("pwd", help="Print current remote working directory")
    subparsers.add_parser("cat", help="Show content of a Google Drive file")
    subparsers.add_parser("read", help="Display remote file with line numbers")
    subparsers.add_parser("grep", help="Search for patterns in remote files")
    subparsers.add_parser("linter", help="Lint a remote file locally")
    subparsers.add_parser("edit", help="Edit a remote file")
    subparsers.add_parser("venv", help="Manage remote virtual environments")
    subparsers.add_parser("bg", help="Run commands in background")
    
    # Special-purpose --options (non-bash, tool-specific)
    parser.add_argument("--setup-tutorial", action="store_true", help="Run the GCS setup tutorial")
    parser.add_argument("--remount", action="store_true", help="Generate and show Colab remount script")
    parser.add_argument("--reconnection", nargs="*", help="API reconnection manager: status, config <count> <duration>, reset")
    parser.add_argument("--shell", nargs="*", help="Interactive shell (no args) or management: list, switch <id>, create <name>, info [id], type [name], install <name>")
    parser.add_argument("--folder-id", help="Target Google Drive folder ID (overrides default)")
    parser.add_argument("--bash", action="store_true", help="Generate bash script instead of Python")
    parser.add_argument("--python", action="store_true", help="Force Python script generation")
    parser.add_argument("--raw", action="store_true", help="Raw command mode: run directly in Colab terminal with result capture")
    parser.add_argument("--no-capture", action="store_true", dest="no_capture", help="No-capture mode: run directly without capturing output (for pip install, long tasks)")
    # --mcp subcommands (boot, shutdown, status, setup-tutorial) are early-intercepted before argparse
    # --mcp-create, --mcp-delete, --mcp-list, --mcp-upload are early-intercepted before argparse
    
    # Decide whether to use tool.handle_command_line based on command recognition
    use_system_fallback = False
    
    # Early intercept remote GUI control commands (--gui-submit, --gui-cancel, --gui-stop, --gui-add-time)
    _gui_cmd_map = {"--gui-submit": "submit", "--gui-cancel": "cancel", "--gui-stop": "stop", "--gui-add-time": "add_time"}
    _gui_match = next((f for f in _gui_cmd_map if f in sys.argv), None)
    if _gui_match:
        from logic.interface.gui import handle_gui_remote_command
        remaining = [a for a in sys.argv[1:] if a not in _gui_cmd_map and a != "--no-warning"]
        sys.exit(handle_gui_remote_command("GOOGLE.GCS", project_root, _gui_cmd_map[_gui_match], remaining, tool.get_translation))

    # Early intercept --mcp: management subcommands or decorator
    # Management: GCS --mcp boot | shutdown | status | setup-tutorial
    # Decorator:  GCS <command> --mcp [--json]
    _MCP_MANAGEMENT_CMDS = {"boot", "shutdown", "status", "setup-tutorial"}
    if "--mcp" in sys.argv:
        import importlib.util
        def _load_mcp_module(name):
            p = Path(__file__).resolve().parent / "logic" / f"{name}.py"
            spec = importlib.util.spec_from_file_location(f"gcs_{name}", str(p))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            return m

        idx = sys.argv.index("--mcp")
        next_arg = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else ""
        next_arg_clean = next_arg.lstrip("-")

        if next_arg_clean in _MCP_MANAGEMENT_CMDS:
            cdp_mod = _load_mcp_module("mcp/cdp_boot")
            if next_arg_clean == "boot":
                sys.exit(cdp_mod.run_mcp_boot())
            elif next_arg_clean == "shutdown":
                sys.exit(cdp_mod.run_mcp_shutdown())
            elif next_arg_clean == "setup-tutorial":
                sys.exit(cdp_mod.run_mcp_setup_tutorial())
            else:
                sys.exit(cdp_mod.run_mcp_status())
        else:
            # MCP decorator: GCS <command> --mcp
            # With CDP: run the normal GCS flow (executor.py handles CDP auto-injection)
            # Without CDP: print workflow instructions for agent
            _cdp_ok = False
            try:
                from logic.cdp.colab import is_chrome_cdp_available
                _cdp_ok = is_chrome_cdp_available()
            except Exception:
                pass

            if _cdp_ok:
                clean = [a for a in sys.argv[1:] if a not in ("--mcp", "--json", "--no-warning", "--python", "--no-feedback")]
                as_json_flag = "--json" in sys.argv
                as_python_flag = "--python" in sys.argv
                command = " ".join(clean)
                if command:
                    mcp_exec = _load_mcp_module("mcp/execute")
                    sys.exit(mcp_exec.run_mcp_execute(command, as_python=as_python_flag, as_json=as_json_flag))
                os.environ["GCS_CDP_ENABLED"] = "1"
                sys.argv = [a for a in sys.argv if a not in ("--mcp", "--json")]
            else:
                print(f"{get_color('BOLD')}{get_color('YELLOW')}Chrome CDP not available{get_color('RESET')}. Run {get_color('BOLD')}GCS --mcp boot{get_color('RESET')} first.")
                print(f"  If not yet configured, run {get_color('BOLD')}GCS --mcp setup-tutorial{get_color('RESET')}.\n")
                clean = [a for a in sys.argv[1:] if a not in ("--mcp", "--json", "--no-warning", "--python")]
                as_json_flag = "--json" in sys.argv
                as_python_flag = "--python" in sys.argv
                command = " ".join(clean)
                if not command:
                    print(f"{get_color('BOLD')}{get_color('RED')}Missing command{get_color('RESET')}. Usage: GCS --mcp <boot|shutdown|status|setup-tutorial> or GCS <command> --mcp")
                    sys.exit(1)
                mcp_exec = _load_mcp_module("mcp/execute")
                sys.exit(mcp_exec.run_mcp_execute(command, as_python=as_python_flag, as_json=as_json_flag))

    # Early intercept MCP Drive operations (complex args, before argparse)
    def _load_mcp_logic(name):
        import importlib.util
        p = Path(__file__).resolve().parent / "logic" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"gcs_{name}", str(p))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    if "--mcp-create" in sys.argv:
        idx = sys.argv.index("--mcp-create")
        mcp_args = sys.argv[idx + 1:]
        as_json_flag = "--json" in mcp_args
        mcp_args = [a for a in mcp_args if a not in ("--json", "--no-warning")]
        file_type = mcp_args[0] if mcp_args else None
        folder_spec = "~"
        filename = None
        rest = mcp_args[1:]
        if "--name" in rest:
            ni = rest.index("--name")
            if ni + 1 < len(rest):
                filename = rest[ni + 1]
            rest = rest[:ni] + rest[ni + 2:]
        if rest:
            folder_spec = rest[0]
        if not file_type:
            print(f"{get_color('BOLD')}{get_color('RED')}Missing type{get_color('RESET')}. Usage: GCS --mcp-create TYPE [FOLDER] [--name NAME]")
            sys.exit(1)
        mcp_cr = _load_mcp_logic("mcp/create")
        sys.exit(mcp_cr.run_mcp_create(file_type, folder_spec, filename, as_json=as_json_flag))

    if "--mcp-delete" in sys.argv:
        idx = sys.argv.index("--mcp-delete")
        mcp_args = sys.argv[idx + 1:]
        as_json_flag = "--json" in mcp_args
        mcp_args = [a for a in mcp_args if a not in ("--json", "--no-warning")]
        file_id = mcp_args[0] if mcp_args else None
        if not file_id:
            print(f"{get_color('BOLD')}{get_color('RED')}Missing file ID{get_color('RESET')}. Usage: GCS --mcp-delete FILE_ID")
            sys.exit(1)
        mcp_cr = _load_mcp_logic("mcp/create")
        sys.exit(mcp_cr.run_mcp_delete(file_id, as_json=as_json_flag))

    if "--mcp-list" in sys.argv:
        idx = sys.argv.index("--mcp-list")
        mcp_args = sys.argv[idx + 1:]
        as_json_flag = "--json" in mcp_args
        mcp_args = [a for a in mcp_args if a not in ("--json", "--no-warning")]
        folder_spec = mcp_args[0] if mcp_args else "~"
        mcp_cr = _load_mcp_logic("mcp/create")
        sys.exit(mcp_cr.run_mcp_list(folder_spec, as_json=as_json_flag))

    if "--mcp-upload" in sys.argv:
        idx = sys.argv.index("--mcp-upload")
        mcp_args = sys.argv[idx + 1:]
        as_json_flag = "--json" in mcp_args
        mcp_args = [a for a in mcp_args if a not in ("--json", "--no-warning")]
        folder_spec = mcp_args[0] if mcp_args else "~"
        mcp_cr = _load_mcp_logic("mcp/create")
        sys.exit(mcp_cr.run_mcp_upload(folder_spec, as_json=as_json_flag))

    # Handle --options that should be intercepted before argparse
    as_python = "--python" in sys.argv
    as_raw = "--raw" in sys.argv
    as_no_capture = "--no-capture" in sys.argv
    as_no_feedback = "--no-feedback" in sys.argv
    if "--python" in sys.argv:
        sys.argv.remove("--python")
    if "--bash" in sys.argv:
        sys.argv.remove("--bash")
        as_python = False
    if "--raw" in sys.argv:
        sys.argv.remove("--raw")
    if "--no-capture" in sys.argv:
        sys.argv.remove("--no-capture")
    if "--no-feedback" in sys.argv:
        sys.argv.remove("--no-feedback")
    
    # Check for special --options first
    special_options = ["--setup-tutorial", "--remount", "--reconnection", "--shell", "--mcp-create", "--mcp-delete", "--mcp-list", "--mcp-upload", "--mcp"]
    has_special = any(opt in sys.argv for opt in special_options)

    if len(sys.argv) > 1 and sys.argv[1] not in recognized and not sys.argv[1].startswith("-") and not has_special:
        use_system_fallback = True
        
    if not use_system_fallback:
        if tool.handle_command_line(parser): return
        args, unknown = parser.parse_known_args()
    else:
        tool.check_cpu_load_and_warn()
        tool.is_quiet = "--tool-quiet" in sys.argv
        clean_argv = [a for a in sys.argv if a not in ["--no-warning", "--tool-quiet"]]
        args = argparse.Namespace(command=None, setup_tutorial=False, remount=False, reconnection=None, shell=None, folder_id=None)
        unknown = clean_argv[1:]

    # Use importlib to load logic from the current directory
    import importlib.util
    def load_logic(name):
        logic_path = Path(__file__).resolve().parent / "logic" / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"gcs_logic_{name}", str(logic_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    state_mod = load_logic("state")
    state_mgr = state_mod.GCSStateManager(tool.project_root)

    # Remote command logic
    remote_command = None
    if not args.command:
        if unknown: remote_command = " ".join(unknown)
        elif not getattr(args, 'setup_tutorial', False) and not getattr(args, 'remount', False) and getattr(args, 'reconnection', None) is None and getattr(args, 'shell', None) is None:
            parser.print_help()
            return
    elif args.command not in recognized:
        remote_command = " ".join([args.command] + unknown)

    # --- Dispatch to command modules ---

    def load_command(name):
        return load_logic(f"command/{name}")

    if getattr(args, 'shell', None) is not None:
        shell_cmd = load_command("shell")
        if not args.shell:
            shell_cmd.enter_interactive(tool, state_mgr, load_logic, as_python)
        else:
            shell_cmd.manage(tool, args.shell, state_mgr, load_logic=load_logic)
        return

    if getattr(args, 'reconnection', None) is not None:
        _handle_reconnection(tool, args.reconnection)
        return

    if getattr(args, 'remount', False):
        code = load_command("remount_cmd").execute(tool, args, state_mgr, load_logic, no_feedback=as_no_feedback)
        if code: sys.exit(code)
        return

    if remote_command:
        if as_no_capture:
            code = load_command("raw_cmd").execute(tool, remote_command, state_mgr, load_logic, no_capture=True, no_feedback=as_no_feedback)
        elif as_raw:
            code = load_command("raw_cmd").execute(tool, remote_command, state_mgr, load_logic, no_feedback=as_no_feedback)
        else:
            code = load_command("remote").execute(tool, remote_command, state_mgr, load_logic, as_python=as_python, no_feedback=as_no_feedback)
        if code: sys.exit(code)
        return

    if getattr(args, 'setup_tutorial', False):
        code = load_command("tutorial_cmd").execute(tool)
        if code: sys.exit(code)
        return

    if args.command == "pwd":
        load_command("pwd").execute(tool, args, state_mgr, load_logic)
        return

    if args.command == "cd":
        code = load_command("cd").execute(tool, args, state_mgr, load_logic)
        if code: sys.exit(code)
        return

    if args.command == "ls":
        code = load_command("ls").execute(tool, args, state_mgr, load_logic)
        if code: sys.exit(code)
        return

    if args.command == "upload":
        code = load_command("upload").execute(tool, args, state_mgr, load_logic, as_python=as_python)
        if code: sys.exit(code)
        return

    if args.command == "cat":
        code = load_command("cat").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "read":
        code = load_command("read").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "grep":
        code = load_command("grep").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "linter":
        code = load_command("linter").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "edit":
        code = load_command("edit").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "venv":
        code = load_command("venv").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

    if args.command == "bg":
        code = load_command("bg").execute(tool, args, state_mgr, load_logic, unknown=unknown)
        if code: sys.exit(code)
        return

def _handle_reconnection(tool, reconnection_args):
    """Handle --reconnection subcommands: status, config, reset."""
    from logic.interface.config import get_color
    gcs_logic_dir = str(tool.project_root / "tool" / "GOOGLE.GCS" / "logic")
    if gcs_logic_dir not in sys.path:
        sys.path.insert(0, gcs_logic_dir)
    from reconnection_manager import (
        get_thresholds, save_thresholds,
        get_execution_counter, reset_execution_counter,
        is_remount_flagged, clear_remount_required_flag,
        is_remount_in_progress,
    )

    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    BLUE = get_color("BLUE")
    YELLOW = get_color("YELLOW")
    RED = get_color("RED")
    RESET = get_color("RESET")

    sub = reconnection_args[0] if reconnection_args else "status"

    if sub == "status":
        count_thresh, dur_thresh = get_thresholds(tool.project_root)
        counter = get_execution_counter(tool.project_root)
        flagged = is_remount_flagged(tool.project_root)
        in_progress = is_remount_in_progress(tool.project_root)

        print(f"{BOLD}GCS API Reconnection Status{RESET}")
        print(f"  Commands executed:   {BLUE}{counter.get('count', 0)}{RESET} / {count_thresh}")
        print(f"  Duration threshold:  {dur_thresh}s")
        print(f"  Remount flagged:     {YELLOW if flagged else GREEN}{'Yes' if flagged else 'No'}{RESET}")
        print(f"  Remount in progress: {YELLOW if in_progress else GREEN}{'Yes' if in_progress else 'No'}{RESET}")

    elif sub == "config":
        if len(reconnection_args) < 3:
            print(f"{RED}Usage:{RESET} GCS --reconnection config <command_count> <duration_seconds>")
            return
        try:
            new_count = int(reconnection_args[1])
            new_dur = float(reconnection_args[2])
        except ValueError:
            print(f"{RED}Error:{RESET} count must be int, duration must be float")
            return
        save_thresholds(tool.project_root, new_count, new_dur)
        print(f"{GREEN}Thresholds updated:{RESET} count={new_count}, duration={new_dur}s")

    elif sub == "reset":
        reset_execution_counter(tool.project_root)
        clear_remount_required_flag(tool.project_root)
        print(f"{GREEN}Reconnection counter and flags cleared.{RESET}")

    else:
        print(f"{YELLOW}Unknown subcommand:{RESET} {sub}")
        print(f"Usage: GCS --reconnection [status|config <count> <duration>|reset]")


if __name__ == "__main__":
    main()
