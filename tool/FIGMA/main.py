#!/usr/bin/env python3
"""FIGMA - Figma design tool automation via CDMCP."""
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("FIGMA")

    parser = argparse.ArgumentParser(
        description="Figma design automation via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("boot", help="Boot Figma session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Manually trigger recovery")
    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("files", help="List design files")
    sub.add_parser("layers", help="List layers in current file")
    sub.add_parser("home", help="Navigate to Figma home")

    p_open = sub.add_parser("open", help="Open a design file")
    p_open.add_argument("title", help="File title to open")

    p_shot = sub.add_parser("screenshot", help="Take a screenshot")
    p_shot.add_argument("--output", default=None, help="Output file path")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.FIGMA.logic.chrome.api import (
        get_auth_state, get_page_info, list_files, open_file,
        take_screenshot, navigate_home, get_layers,
        boot_session, get_session_status, _recover,
    )

    if args.command == "boot":
        r = boot_session()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Booted{RESET} Figma session.")
            print(f"  State: {r.get('state', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "session":
        s = get_session_status()
        print(f"  State: {BOLD}{s.get('state', '?')}{RESET}")
        print(f"  Active: {'Yes' if s.get('session_active') else 'No'}")
        if s.get("last_url"):
            print(f"  URL: {s['last_url'][:60]}")
        if s.get("last_file_name"):
            print(f"  File: {s['last_file_name']}")

    elif args.command == "recover":
        r = _recover()
        if r:
            print(f"  {BOLD}{GREEN}Recovered{RESET}.")
        else:
            print(f"  {BOLD}{RED}Recovery failed{RESET}.")

    elif args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "files":
        r = list_files()
        if r.get("ok"):
            files = r.get("files", [])
            print(f"  Found {r.get('count', 0)} files:")
            for i, f in enumerate(files):
                print(f"    [{i+1}] {f.get('title', '?'):<50} {f.get('modified', '')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "open":
        r = open_file(args.title)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Opened{RESET} '{args.title}'.")
            print(f"  URL: {r.get('url', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "layers":
        r = get_layers()
        if r.get("ok"):
            layers = r.get("layers", [])
            print(f"  Found {r.get('count', 0)} layers:")
            for l in layers:
                print(f"    {l.get('name', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "home":
        r = navigate_home()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Navigated{RESET} to home.")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "screenshot":
        r = take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Screenshot saved:{RESET} {r['path']} ({r['size']} bytes)")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
