#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("LINEAR")

    parser = argparse.ArgumentParser(
        description="Linear product development via Chrome CDP",
        epilog="MCP commands use --mcp- prefix: e.g., LINEAR --mcp-status, LINEAR --mcp-page",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("status", help="Check authentication and organization state")
    sub.add_parser("me", help="Show user info")
    sub.add_parser("page", help="Show current page state")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.LINEAR.logic.chrome.api import (
        get_auth_state, get_user_info, get_page_info,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        if r.get("email"):
            print(f"  Email: {r['email']}")
        has_orgs = r.get("hasOrganizations", False)
        orgs = r.get("availableOrgs", [])
        print(f"  Organizations: {len(orgs) if orgs else ('Yes' if has_orgs else 'None')}")
        if not has_orgs and not orgs:
            print(f"  {YELLOW}No organizations — create or join one at linear.app{RESET}")

    elif args.command == "me":
        r = get_user_info()
        if r.get("ok"):
            d = r["data"]
            print(f"  Account ID: {d.get('accountId', '?')}")
            print(f"  Email:      {d.get('email', '?')}")
            orgs = d.get("organizations", [])
            avail = d.get("availableOrganizations", [])
            if orgs:
                for o in orgs:
                    print(f"  Org:        {o.get('name', '?')} ({o.get('id', '?')[:8]}...)")
            elif avail:
                for o in avail:
                    print(f"  Available:  {o.get('name', '?')} ({o.get('urlKey', '?')})")
            else:
                print(f"  {YELLOW}No organizations linked{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title: {r.get('title', '?')}")
            print(f"  URL:   {r.get('url', '?')}")
            print(f"  Path:  {r.get('pathname', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
