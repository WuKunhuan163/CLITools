#!/usr/bin/env python3
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

from logic.interface.tool import ToolBase
from logic.interface.config import get_color


def main():
    tool = ToolBase("XMIND")

    parser = argparse.ArgumentParser(
        description="XMind mind mapping via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("maps", help="List mind maps (requires auth)")
    sub.add_parser("sidebar", help="Show sidebar sections (requires auth)")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.XMIND.logic.chrome.api import (
        get_auth_state, get_page_info, get_maps, get_sidebar,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")
        if r.get("isLogin"):
            print(f"  {YELLOW}On login page{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "maps":
        r = get_maps()
        if r.get("ok"):
            maps = r.get("maps", [])
            print(f"  Found {r.get('count', 0)} maps")
            for i, m in enumerate(maps):
                print(f"  [{i+1}] {m['title']:<50} {m.get('time','')}")
            if not maps:
                print(f"  {YELLOW}No maps visible{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "sidebar":
        r = get_sidebar()
        if r.get("ok"):
            for s in r.get("sections", []):
                print(f"  {s}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
