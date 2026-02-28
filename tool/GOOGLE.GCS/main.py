#!/usr/bin/env python3 -u

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
    
    # Remove script dir from path to avoid shadowing
    script_dir = str(Path(__file__).resolve().parent)
    if script_dir in sys.path:
        sys.path.remove(script_dir)
else:
    # Fallback
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

def main():
    # PERFORMANCE OPTIMIZATION: Force IPv4 for Google API requests.
    import socket
    try:
        import urllib3.util.connection as urllib3_cn
        def allowed_gai_family():
            return socket.AF_INET # Force IPv4
        urllib3_cn.allowed_gai_family = allowed_gai_family
    except:
        pass

    tool = ToolBase("GOOGLE.GCS")
    
    parser = argparse.ArgumentParser(description="Google Drive Remote Controller (GCS)", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")
    
    # Recognized built-in commands
    recognized = ["ls", "cat", "cd", "pwd", "setup-tutorial", "remount", "shell", "status", "setup", "config", "install", "uninstall", "rule", "-h", "--help", "help"]
    
    # Existing commands
    ls_parser = subparsers.add_parser("ls", help="List files in a Google Drive folder")
    ls_parser.add_argument("path", nargs="?", default=None, help="Remote path (~ = root, @ = env, e.g. ~/tmp)")
    ls_parser.add_argument("-l", action="store_true", help="Long format listing (shows IDs and types)")
    
    subparsers.add_parser("cat", help="Show content of a Google Drive file")
    
    cd_parser = subparsers.add_parser("cd", help="Change remote working directory")
    cd_parser.add_argument("path", nargs="?", default="~", help="Remote path (~ = root, @ = env, or relative)")
    
    subparsers.add_parser("pwd", help="Print current remote working directory")
    
    subparsers.add_parser("setup-tutorial", help="Run the GCS setup tutorial")
    subparsers.add_parser("remount", help="Generate and show Colab remount script")
    
    shell_parser = subparsers.add_parser("shell", help="Manage logical shells")
    shell_parser.add_argument("action", choices=["list", "switch", "create", "info"], help="Action to perform")
    shell_parser.add_argument("name_or_id", nargs="?", help="Shell name (for create) or ID (for switch/info)")
    
    subparsers.add_parser("status", help="Show GCS and shell status")
    
    parser.add_argument("--folder-id", help="Target Google Drive folder ID (overrides default)")
    parser.add_argument("--bash", action="store_true", help="Generate bash script instead of Python (for Colab terminal)")
    parser.add_argument("--python", action="store_true", help="Force Python script generation (default)")
    
    # Decide whether to use tool.handle_command_line based on command recognition
    use_system_fallback = False
    
    as_python = "--python" in sys.argv
    if "--python" in sys.argv:
        sys.argv.remove("--python")
    if "--bash" in sys.argv:
        sys.argv.remove("--bash")
        as_python = False

    if len(sys.argv) > 1 and sys.argv[1] not in recognized and not sys.argv[1].startswith("-"):
        use_system_fallback = True
        
    if not use_system_fallback:
        if tool.handle_command_line(parser): return
        args, unknown = parser.parse_known_args()
    else:
        # Unknown command - we treat it as a remote command later
        tool.check_cpu_load_and_warn()
        tool.is_quiet = "--tool-quiet" in sys.argv
        # Strip internal flags
        clean_argv = [a for a in sys.argv if a not in ["--no-warning", "--tool-quiet"]]
        args = argparse.Namespace(command=None)
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
        else:
            parser.print_help()
            return
    elif args.command not in recognized:
        remote_command = " ".join([args.command] + unknown)

    if args.command == "status":
        BOLD, GREEN, BLUE, RESET = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET")
        sid = state_mgr.get_active_shell_id()
        info = state_mgr.get_shell_info(sid)
        print(f"{BOLD}GCS Status:{RESET}")
        print(f"  Active Shell ID: {BLUE}{sid}{RESET}")
        print(f"  Active Shell Name: {info['name']}")
        print(f"  Remote CWD: {info['remote_cwd']}")
        return

    if args.command == "shell":
        BOLD, GREEN, BLUE, RESET = get_color("BOLD"), get_color("GREEN"), get_color("BLUE"), get_color("RESET")
        if args.action == "list":
            shells = state_mgr.list_shells()
            active_id = state_mgr.get_active_shell_id()
            print(f"{BOLD}Logical Shells:{RESET}")
            for sid, sname, last_used in shells:
                mark = f"{GREEN}* {RESET}" if sid == active_id else "  "
                print(f"{mark}{BLUE}{sid}{RESET} ({sname}) - Last used: {last_used}")
        elif args.action == "create":
            if not args.name_or_id: print(f"Usage: GOOGLE.GCS shell create <name>"); return
            new_id = state_mgr.create_shell(args.name_or_id)
            print(f"{BOLD}{GREEN}Created and switched to shell{RESET}: {args.name_or_id} (ID: {BLUE}{new_id}{RESET})")
        elif args.action == "switch":
            if not args.name_or_id: print(f"Usage: GOOGLE.GCS shell switch <id>"); return
            if state_mgr.switch_shell(args.name_or_id): print(f"{BOLD}{GREEN}Switched to shell{RESET}: {BLUE}{args.name_or_id}{RESET}")
            else: print(f"{BOLD}{get_color('RED')}Error{RESET}: Shell ID {args.name_or_id} not found.")
        elif args.action == "info":
            info = state_mgr.get_shell_info(args.name_or_id)
            if info:
                print(f"{BOLD}Shell Info ({args.name_or_id or state_mgr.get_active_shell_id()}):{RESET}")
                for k, v in info.items(): print(f"  {k}: {v}")
            else: print(f"{BOLD}{get_color('RED')}Error{RESET}: Shell not found.")
        return

    if args.command == "remount" or remote_command:
        from logic.turing.models.progress import ProgressTuringMachine
        from logic.turing.logic import TuringStage
        from logic.gui.manager import run_gui_subprocess
        pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="GCS", log_dir=tool.get_log_dir())
        
        if args.command == "remount":
            remount_mod = load_logic("remount")
            script, metadata = remount_mod.generate_remount_script(tool.project_root)
            if not script: print(f"{get_color('BOLD')}{get_color('RED')}Error{get_color('RESET')}: {metadata}"); sys.exit(1)
            logic_script = Path(__file__).resolve().parent / "logic" / "remount.py"
            gui_args = ["--script-path", "", "--ts", metadata["ts"], "--hash", metadata["session_hash"], "--project-root", str(tool.project_root)]
            def gui_action(stage=None):
                tmp_script = tool.project_root / "tmp" / f"gcs_remount_{metadata['ts']}.py"
                tmp_script.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_script, 'w') as f: f.write(script)
                gui_args[1] = str(tmp_script)
                old_quiet = getattr(tool, "is_quiet", False)
                tool.is_quiet = True
                try: res = run_gui_subprocess(tool, sys.executable, str(logic_script), 300, args=gui_args)
                finally: tool.is_quiet = old_quiet
                if tmp_script.exists(): tmp_script.unlink()
                return res.get("status") == "success"
            def verify_action(stage=None):
                import time
                time.sleep(1.0)
                ok, msg = remount_mod.verify_local_remount_result(tool.project_root, metadata["ts"], metadata["session_hash"], stage=stage)
                if not ok and stage: stage.fail_status, stage.fail_name, stage.error_brief = "Failed to verify", "remount result", msg
                return ok
            pm.add_stage(TuringStage("user action", gui_action, active_status="Waiting for", active_name="user action", fail_status="Failed to complete", stealth=True, bold_part="Waiting for user action"))
            pm.add_stage(TuringStage("result file", verify_action, active_status="Verifying", active_name="the remount result file", fail_status="Failed to verify", fail_name="remount result", stealth=True, bold_part="Verifying the remount result file"))
            if pm.run(ephemeral=True): 
                print(f"{get_color('BOLD')}{get_color('GREEN')}Successfully remounted{get_color('RESET')} Google Drive from Google Colab.")
                config_path = tool.project_root / "data" / "config.json"
                if config_path.exists():
                    import json
                    with open(config_path, "r") as f:
                        cfg = json.load(f)
                    cfg["mount_hash"] = metadata["session_hash"]
                    with open(config_path, "w") as f:
                        json.dump(cfg, f, indent=2)
            return

        if remote_command:
            executor_mod = load_logic("executor")
            sid = state_mgr.get_active_shell_id()
            info = state_mgr.get_shell_info(sid)
            script, metadata = executor_mod.generate_remote_command_script(tool.project_root, remote_command, remote_cwd=info["remote_cwd"], as_python=as_python)
            logic_script = Path(__file__).resolve().parent / "logic" / "executor.py"
            gui_args = ["--command", remote_command, "--script-path", "", "--project-root", str(tool.project_root)]
            if as_python: gui_args.append("--as-python")
            command_result = {}
            def gui_action(stage=None):
                tmp_script = tool.project_root / "tmp" / f"gcs_cmd_{metadata['ts']}.py"
                tmp_script.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp_script, 'w') as f: f.write(script)
                gui_args[3] = str(tmp_script)
                old_quiet = getattr(tool, "is_quiet", False)
                tool.is_quiet = True
                try: res = run_gui_subprocess(tool, sys.executable, str(logic_script), 600, args=gui_args)
                finally: tool.is_quiet = old_quiet
                if tmp_script.exists(): tmp_script.unlink()
                return res.get("status") == "success"
            def verify_action(stage=None):
                common_mod = load_logic("common")
                import time
                time.sleep(1.0)
                ok, msg, data = common_mod.wait_for_gdrive_file(tool.project_root, metadata["result_filename"], timeout=60, stage=stage)
                if ok: 
                    command_result.update(data)
                    return True
                if stage: stage.fail_status, stage.fail_name, stage.error_brief = "Failed to execute", "command", msg
                return False
            pm.add_stage(TuringStage("user action", gui_action, active_status="Waiting for", active_name="user action", fail_status="Failed to complete", stealth=True, bold_part="Waiting for user action"))
            pm.add_stage(TuringStage("command execution", verify_action, active_status="Verifying", active_name="the command result file", fail_status="Failed to execute", fail_name="command", stealth=True, bold_part="Verifying the command result file"))
            if pm.run(ephemeral=True):
                if "stdout" in command_result: print(command_result["stdout"], end="")
                if "stderr" in command_result and command_result["stderr"]: print(f"{get_color('RED')}{command_result['stderr']}{get_color('RESET')}", file=sys.stderr, end="")
                if command_result.get("returncode") != 0: sys.exit(command_result.get("returncode", 1))
            return

    if args.command == "setup-tutorial":
        import importlib.util
        tutorial_path = Path(__file__).resolve().parent / "logic" / "tutorial" / "setup_guide" / "main.py"
        spec = importlib.util.spec_from_file_location("google_gcs_tutorial", str(tutorial_path))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        res = module.run_setup_tutorial()
        if res.get("status") == "success": print(f"{get_color('BOLD')}{get_color('GREEN')}Successfully completed{get_color('RESET')} GCS setup tutorial.")
        else:
            reason = res.get('reason') or res.get('status') or 'Unknown'
            print(f"{get_color('BOLD')}{get_color('RED')}Tutorial exited{get_color('RESET')}: {reason}")
        return

    if args.command == "pwd":
        shell_info = state_mgr.get_shell_info()
        current_path = shell_info.get("current_path", "~") if shell_info else "~"
        print(current_path)
        return

    if args.command == "cd":
        import json, requests
        common = load_logic("common")
        BOLD = get_color("BOLD")
        RED = get_color("RED")
        RESET = get_color("RESET")

        config = common.get_gcs_config(tool.project_root)
        if not config:
            print(f"{BOLD}{RED}Error{RESET}: GCS config not found. Run 'setup-tutorial'.")
            return
        creds = common.get_service_account_creds(tool.project_root)
        if not creds:
            print(f"{BOLD}{RED}Error{RESET}: Credentials not found. Run 'setup-tutorial'.")
            return

        try:
            token = common.get_gdrive_access_token(creds)
            if not token:
                print(f"{BOLD}{RED}Error{RESET}: Failed to obtain access token.")
                return
            headers = {"Authorization": f"Bearer {token}"}

            shell_info = state_mgr.get_shell_info()
            cur_path = shell_info.get("current_path", "~") if shell_info else "~"
            cur_fid = shell_info.get("current_folder_id") if shell_info else None

            folder_id, display_path = common.resolve_drive_path(
                headers, args.path, config,
                current_path=cur_path, current_folder_id=cur_fid
            )
            if not folder_id:
                print(f"{BOLD}{RED}Error{RESET}: {display_path}")
                return

            shell_id = state_mgr.get_active_shell_id()
            state_mgr.update_shell(shell_id, current_path=display_path, current_folder_id=folder_id)
            print(display_path)
        except Exception as e:
            print(f"{BOLD}{RED}Error{RESET}: {e}")
        return

    if args.command in ["ls", "cat"]:
        import json, requests
        common = load_logic("common")
        
        BOLD = get_color("BOLD")
        RED = get_color("RED")
        RESET = get_color("RESET")
        
        config = common.get_gcs_config(tool.project_root)
        if not config:
            print(f"{BOLD}{RED}Error{RESET}: GCS config not found. Please run 'setup-tutorial'.")
            return
        creds = common.get_service_account_creds(tool.project_root)
        if not creds:
            print(f"{BOLD}{RED}Error{RESET}: Credentials not found. Please run 'setup-tutorial'.")
            return
        
        try:
            token = common.get_gdrive_access_token(creds)
            if not token:
                print(f"{BOLD}{RED}Error{RESET}: Failed to obtain access token.")
                return
            headers = {"Authorization": f"Bearer {token}"}
            
            if args.command == "ls":
                shell_info = state_mgr.get_shell_info()
                cur_path = shell_info.get("current_path", "~") if shell_info else "~"
                cur_fid = shell_info.get("current_folder_id") if shell_info else None
                
                ls_path = args.path if args.path is not None else cur_path
                
                if args.folder_id:
                    folder_id = args.folder_id
                    display_path = folder_id
                else:
                    folder_id, display_path = common.resolve_drive_path(
                        headers, ls_path, config,
                        current_path=cur_path, current_folder_id=cur_fid
                    )
                    if not folder_id:
                        print(f"{BOLD}{RED}Error{RESET}: {display_path}")
                        return
                
                import uuid
                params = {
                    "q": f"'{folder_id}' in parents and trashed = false",
                    "fields": "files(id, name, mimeType, size, modifiedTime)",
                    "pageSize": 200,
                    "supportsAllDrives": "true",
                    "includeItemsFromAllDrives": "true",
                    "quotaUser": f"ls_{uuid.uuid4().hex[:8]}"
                }
                res = requests.get("https://www.googleapis.com/drive/v3/files", headers=headers, params=params, timeout=20)
                if res.status_code == 200:
                    files = res.json().get("files", [])
                    files.sort(key=lambda f: f.get("name", "").lower())
                    if args.l:
                        print(f"\n{BOLD}{display_path}:{RESET}")
                        for f in files:
                            name = f['name']
                            if f['mimeType'] == 'application/vnd.google-apps.folder':
                                name += "/"
                            print(f"  {f['id']:<44} {name}")
                    else:
                        for f in files:
                            name = f['name']
                            if f['mimeType'] == 'application/vnd.google-apps.folder':
                                name += "/"
                            print(name)
                else:
                    print(f"{BOLD}{RED}Error{RESET}: API returned {res.status_code}: {res.text}")
                    
            elif args.command == "cat":
                file_id = unknown[0] if unknown else None
                if not file_id:
                    print("Usage: GOOGLE.GCS cat <FILE_ID>")
                    return
                res = requests.get(f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media", headers=headers, timeout=15)
                if res.status_code == 200:
                    print(res.text)
                else:
                    print(f"{BOLD}{RED}Error{RESET}: API returned {res.status_code}: {res.text}")
        except Exception as e:
            print(f"{BOLD}{RED}Error{RESET}: {e}")
        return

if __name__ == "__main__":
    main()
