#!/usr/bin/env python3
"""GDS --shell command: interactive REPL and shell management."""
import subprocess
import os
from interface.config import get_color


def enter_interactive(tool, state_mgr, load_logic, default_as_python=False):
    """Interactive REPL shell mode. Commands are dispatched as GDS subcommands."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    BLUE = get_color("BLUE")
    RED = get_color("RED")
    RESET = get_color("RESET")

    print(f"{BOLD}GDS Interactive Shell{RESET}")
    print(f"Type commands as if prefixed with 'GDS'. Type {BOLD}exit{RESET} to quit, {BOLD}help{RESET} for usage.\n")

    while True:
        try:
            shell_info = state_mgr.get_shell_info()
            current_path = shell_info.get("current_path", "~") if shell_info else "~"
            shell_type = shell_info.get("shell_type", "bash") if shell_info else "bash"
            if current_path == "~":
                display_path = "~"
            else:
                parts = current_path.rstrip("/").split("/")
                display_path = parts[-1] if parts[-1] else "~"

            type_label = f"({shell_type})" if shell_type != "bash" else ""
            prompt = f"{BLUE}GDS{type_label}{RESET}:{GREEN}{display_path}{RESET}$ "
            try:
                user_input = input(prompt).strip()
            except (EOFError, KeyboardInterrupt):
                print(f"\n{BOLD}Exiting{RESET} GDS shell.")
                return

            if not user_input:
                continue

            parts = user_input.split()
            cmd = parts[0].lower()

            if cmd in ("exit", "quit"):
                print(f"{BOLD}Exiting{RESET} GDS shell.")
                return

            if cmd == "help":
                _print_help()
                continue

            tool_bin = os.environ.get("GDS_BIN_PATH", "GDS")
            cmd_args = [tool_bin] + parts
            try:
                subprocess.run(cmd_args, timeout=120)
            except subprocess.TimeoutExpired:
                print(f"{BOLD}{RED}Command timed out{RESET}.")
            except FileNotFoundError:
                print(f"{BOLD}{RED}Error{RESET}: GDS executable not found. Ensure GDS is installed.")
            except KeyboardInterrupt:
                print()

        except KeyboardInterrupt:
            print()
            continue


def manage(tool, shell_args, state_mgr, **kwargs):
    """Handle shell management subcommands: list, create, switch, info."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    BLUE = get_color("BLUE")
    RED = get_color("RED")
    RESET = get_color("RESET")

    action = shell_args[0]
    name_or_id = shell_args[1] if len(shell_args) > 1 else None

    if action == "list":
        shells = state_mgr.list_shells()
        active_id = state_mgr.get_active_shell_id()
        print(f"{BOLD}Logical Shells:{RESET}")
        for sid, sname, last_used in shells:
            mark = f"{GREEN}* {RESET}" if sid == active_id else "  "
            print(f"{mark}{BLUE}{sid}{RESET} ({sname}) - Last used: {last_used}")
    elif action == "create":
        if not name_or_id:
            print("Usage: GDS --shell create <name>")
            return
        new_id = state_mgr.create_shell(name_or_id)
        print(f"{BOLD}{GREEN}Created and switched to shell{RESET}: {name_or_id} (ID: {BLUE}{new_id}{RESET})")
    elif action == "switch":
        if not name_or_id:
            print("Usage: GDS --shell switch <id>")
            return
        if state_mgr.switch_shell(name_or_id):
            print(f"{BOLD}{GREEN}Switched to shell{RESET}: {BLUE}{name_or_id}{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: Shell ID {name_or_id} not found.")
    elif action == "type":
        shell_id = state_mgr.get_active_shell_id()
        info = state_mgr.get_shell_info(shell_id)
        if not name_or_id:
            current_type = info.get("shell_type", "bash") if info else "bash"
            print(f"Current shell type: {BOLD}{current_type}{RESET}")
        else:
            supported = ["bash", "sh", "zsh", "fish"]
            if name_or_id not in supported:
                print(f"{BOLD}{RED}Error{RESET}: Unknown shell type '{name_or_id}'. Supported: {', '.join(supported)}")
                return
            state_mgr.update_shell(shell_id, shell_type=name_or_id)
            print(f"{BOLD}{GREEN}Switched{RESET} shell type to {BOLD}{name_or_id}{RESET}.")
    elif action == "install":
        if not name_or_id:
            print("Usage: GDS --shell install <shell_name>  (e.g. zsh, fish)")
            return
        _install_shell(tool, name_or_id, state_mgr, load_logic=kwargs.get("load_logic"))
    elif action == "info":
        info = state_mgr.get_shell_info(name_or_id)
        if info:
            print(f"{BOLD}Shell Info ({name_or_id or state_mgr.get_active_shell_id()}):{RESET}")
            for k, v in info.items():
                print(f"  {k}: {v}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: Shell not found.")


def _install_shell(tool, shell_name, state_mgr, load_logic=None):
    """Install a shell binary on the remote Colab environment."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    install_scripts = {
        "zsh": (
            "apt-get update -qq && apt-get install -y -qq zsh > /dev/null 2>&1 && "
            "mkdir -p /content/drive/MyDrive/REMOTE_ENV/shell/zsh/bin && "
            "cp $(which zsh) /content/drive/MyDrive/REMOTE_ENV/shell/zsh/bin/zsh && "
            "echo 'zsh installed successfully'"
        ),
        "fish": (
            "apt-get update -qq && apt-get install -y -qq fish > /dev/null 2>&1 && "
            "mkdir -p /content/drive/MyDrive/REMOTE_ENV/shell/fish/bin && "
            "cp $(which fish) /content/drive/MyDrive/REMOTE_ENV/shell/fish/bin/fish && "
            "echo 'fish installed successfully'"
        ),
    }

    if shell_name not in install_scripts:
        print(f"{BOLD}{RED}Error{RESET}: No install script for '{shell_name}'. Available: {', '.join(install_scripts.keys())}")
        return

    if not load_logic:
        print(f"{BOLD}{RED}Error{RESET}: Internal error (load_logic unavailable).")
        return

    print(f"{BOLD}{BLUE}Installing{RESET} {shell_name} on remote...")
    remote_mod = load_logic("command/remote")
    result = remote_mod.execute(tool, install_scripts[shell_name], state_mgr, load_logic, capture=True)

    if result and result.get("returncode", 1) == 0:
        stdout = result.get("stdout", "").strip()
        print(f"{BOLD}{GREEN}Installed{RESET} {shell_name}.")
        if stdout:
            print(stdout)
        shell_id = state_mgr.get_active_shell_id()
        state_mgr.update_shell(shell_id, shell_type=shell_name)
        print(f"Shell type automatically switched to {BOLD}{shell_name}{RESET}.")
    else:
        stderr = result.get("stderr", "") if result else "No result"
        print(f"{BOLD}{RED}Failed{RESET} to install {shell_name}: {stderr}")


def _print_help():
    BOLD = get_color("BOLD")
    RESET = get_color("RESET")
    print(f"{BOLD}GDS Shell Commands:{RESET}")
    print(f"  {BOLD}ls{RESET} [path]       List remote directory")
    print(f"  {BOLD}cd{RESET} [path]       Change remote directory")
    print(f"  {BOLD}pwd{RESET}             Print current remote path")
    print(f"  {BOLD}cat{RESET} <file_id>   Show file content")
    print(f"  {BOLD}help{RESET}            Show this help")
    print(f"  {BOLD}exit{RESET}            Exit shell mode")
    print(f"  {BOLD}--shell type{RESET}    Show current shell type")
    print(f"  {BOLD}--shell type zsh{RESET} Switch to a different shell")
    print(f"  {BOLD}--shell install zsh{RESET} Install a shell on remote")
    print(f"\nOther input is sent as a remote command (via GDS).")
