#!/usr/bin/env python3
"""EXEC -- Shell command execution tool.

A lightweight wrapper for executing shell commands with timeout,
output capture, and structured result reporting.

Usage:
    EXEC run "ls -la"
    EXEC run "python3 script.py" --timeout 30
    EXEC which "python3"
"""
import sys
import subprocess
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists():
        break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def cmd_run(args):
    """Execute a shell command."""
    BOLD = get_color("BOLD")
    get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    command = args.command
    timeout = getattr(args, "timeout", 60)
    cwd = getattr(args, "cwd", None)

    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
        if result.stdout:
            print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            print(f"  {BOLD}{RED}Exit code{RESET}: {result.returncode}")
        sys.exit(result.returncode)
    except subprocess.TimeoutExpired:
        print(f"  {BOLD}{RED}Timed out{RESET} after {timeout}s.")
        sys.exit(124)
    except Exception as e:
        print(f"  {BOLD}{RED}Failed{RESET}: {e}")
        sys.exit(1)


def cmd_sandbox(args):
    """Manage sandbox policies."""
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    DIM = get_color("DIM", "\033[2m")
    RESET = get_color("RESET")

    from tool.EXEC.logic.sandbox import (
        list_policies, set_command_policy, remove_command_policy,
        classify_command, get_blocked_hint,
        ALLOWED_COMMANDS, BLOCKED_COMMANDS,
    )

    action = getattr(args, "action", None)

    if action == "list":
        policies = list_policies()
        if not policies:
            print(f"  {DIM}No custom policies set.{RESET}")
        else:
            for cmd, pol in sorted(policies.items()):
                color = GREEN if pol == "allow" else RED
                print(f"  {BOLD}{cmd}{RESET}: {color}{pol}{RESET}")
        print()
        print(f"  {DIM}Built-in allowed: {', '.join(sorted(ALLOWED_COMMANDS))}{RESET}")
        print(f"  {DIM}Built-in blocked: {', '.join(sorted(BLOCKED_COMMANDS))}{RESET}")

    elif action == "set":
        cmd_name = args.cmd_name
        policy = args.policy
        if policy not in ("allow", "deny"):
            print(f"  {BOLD}{RED}Error{RESET}: policy must be 'allow' or 'deny'.")
            sys.exit(1)
        set_command_policy(cmd_name, policy)
        color = GREEN if policy == "allow" else RED
        print(f"  {BOLD}{GREEN}Set{RESET} {BOLD}{cmd_name}{RESET} -> {color}{policy}{RESET}")

    elif action == "remove":
        cmd_name = args.cmd_name
        if remove_command_policy(cmd_name):
            print(f"  {BOLD}{GREEN}Removed{RESET} policy for {BOLD}{cmd_name}{RESET}")
        else:
            print(f"  {DIM}No policy found for '{cmd_name}'.{RESET}")

    elif action == "check":
        cmd_name = args.cmd_name
        cls = classify_command(cmd_name)
        if cls == "allowed":
            print(f"  {BOLD}{cmd_name}{RESET}: {GREEN}allowed{RESET} (built-in)")
        elif cls == "blocked":
            hint = get_blocked_hint(cmd_name)
            print(f"  {BOLD}{cmd_name}{RESET}: {RED}blocked{RESET} (built-in) -- {hint}")
        elif cls == "policy_allow":
            print(f"  {BOLD}{cmd_name}{RESET}: {GREEN}allowed{RESET} (custom policy)")
        elif cls == "policy_deny":
            print(f"  {BOLD}{cmd_name}{RESET}: {RED}denied{RESET} (custom policy)")
        else:
            print(f"  {BOLD}{cmd_name}{RESET}: unknown (will prompt at runtime)")

    else:
        print(f"  {BOLD}EXEC sandbox{RESET} -- Manage command execution policies.")
        print()
        print(f"  Subcommands:")
        print(f"    list              Show all policies")
        print(f"    set CMD POLICY    Set policy (allow/deny)")
        print(f"    remove CMD        Remove a custom policy")
        print(f"    check CMD         Check command classification")


def cmd_which(args):
    """Find the path of a command."""
    import shutil
    path = shutil.which(args.name)
    if path:
        print(path)
    else:
        BOLD = get_color("BOLD")
        RED = get_color("RED")
        RESET = get_color("RESET")
        print(f"  {BOLD}{RED}Not found{RESET}: {args.name}")
        sys.exit(1)


def main():
    tool = ToolBase("EXEC")

    parser = argparse.ArgumentParser(
        description="EXEC -- Shell command execution",
        add_help=False,
    )

    sub = parser.add_subparsers(dest="subcmd")

    p_run = sub.add_parser("run", help="Execute a shell command")
    p_run.add_argument("command", help="Command to execute")
    p_run.add_argument("--timeout", type=int, default=60, help="Timeout in seconds")
    p_run.add_argument("--cwd", help="Working directory")

    p_which = sub.add_parser("which", help="Find command path")
    p_which.add_argument("name", help="Command name")

    p_sb = sub.add_parser("sandbox", help="Manage sandbox policies")
    sb_sub = p_sb.add_subparsers(dest="action")
    sb_sub.add_parser("list", help="Show all policies")
    sb_set = sb_sub.add_parser("set", help="Set policy for a command")
    sb_set.add_argument("cmd_name", help="Command name")
    sb_set.add_argument("policy", help="'allow' or 'deny'")
    sb_rm = sb_sub.add_parser("remove", help="Remove a command policy")
    sb_rm.add_argument("cmd_name", help="Command name")
    sb_chk = sb_sub.add_parser("check", help="Check command classification")
    sb_chk.add_argument("cmd_name", help="Command name")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()

    BOLD = get_color("BOLD")
    RESET = get_color("RESET")

    if args.subcmd == "run":
        cmd_run(args)
    elif args.subcmd == "which":
        cmd_which(args)
    elif args.subcmd == "sandbox":
        cmd_sandbox(args)
    else:
        print(f"  {BOLD}EXEC{RESET} -- Shell command execution.")
        print()
        print(f"  Commands:")
        print(f"    run \"cmd\"    Execute a shell command (--timeout N, --cwd DIR)")
        print(f"    which NAME   Find the path of a command")
        print(f"    sandbox      Manage sandbox policies (list, set, remove, check)")


if __name__ == "__main__":
    main()
