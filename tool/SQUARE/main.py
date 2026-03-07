#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.interface.config import get_color


def main():
    tool = ToolBase("SQUARE")

    parser = argparse.ArgumentParser(
        description="Square business platform via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("dashboard", help="Show dashboard summary (requires auth)")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.SQUARE.logic.chrome.api import (
        get_auth_state, get_page_info, get_dashboard_info,
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
            if r.get("heading"):
                print(f"  Heading: {r['heading']}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "dashboard":
        r = get_dashboard_info()
        if r.get("ok"):
            d = r.get("data", {})
            print(f"  Merchant: {d.get('merchantName') or '(not visible)'}")
            print(f"  Balance:  {d.get('balance') or '(not visible)'}")
            if d.get("summary"):
                print(f"  Summary:  {d['summary'][:150]}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
