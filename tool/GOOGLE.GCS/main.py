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

from logic.interface.tool import ToolBase
from logic.interface.config import get_color


def main():
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
    parser.add_argument("--shell", nargs="*", help="Interactive shell (no args) or management: list, switch <id>, create <name>, info [id], type [name], install <name>")
    parser.add_argument("--folder-id", help="Target Google Drive folder ID (overrides default)")
    parser.add_argument("--bash", action="store_true", help="Generate bash script instead of Python")
    parser.add_argument("--python", action="store_true", help="Force Python script generation")
    parser.add_argument("--raw", action="store_true", help="Raw command mode: run directly in Colab terminal with result capture")
    parser.add_argument("--no-capture", action="store_true", dest="no_capture", help="No-capture mode: run directly without capturing output (for pip install, long tasks)")
    
    # Decide whether to use tool.handle_command_line based on command recognition
    use_system_fallback = False
    
    # Handle --options that should be intercepted before argparse
    as_python = "--python" in sys.argv
    as_raw = "--raw" in sys.argv
    as_no_capture = "--no-capture" in sys.argv
    if "--python" in sys.argv:
        sys.argv.remove("--python")
    if "--bash" in sys.argv:
        sys.argv.remove("--bash")
        as_python = False
    if "--raw" in sys.argv:
        sys.argv.remove("--raw")
    if "--no-capture" in sys.argv:
        sys.argv.remove("--no-capture")
    
    # Check for special --options first
    special_options = ["--setup-tutorial", "--remount", "--shell"]
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
        args = argparse.Namespace(command=None, setup_tutorial=False, remount=False, shell=None, folder_id=None)
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
        elif not getattr(args, 'setup_tutorial', False) and not getattr(args, 'remount', False) and getattr(args, 'shell', None) is None:
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

    if getattr(args, 'remount', False):
        code = load_command("remount_cmd").execute(tool, args, state_mgr, load_logic)
        if code: sys.exit(code)
        return

    if remote_command:
        if as_no_capture:
            code = load_command("raw_cmd").execute(tool, remote_command, state_mgr, load_logic, no_capture=True)
        elif as_raw:
            code = load_command("raw_cmd").execute(tool, remote_command, state_mgr, load_logic)
        else:
            code = load_command("remote").execute(tool, remote_command, state_mgr, load_logic, as_python=as_python)
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

if __name__ == "__main__":
    main()
