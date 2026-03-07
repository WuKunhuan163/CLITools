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

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("WPS")

    parser = argparse.ArgumentParser(
        description="WPS Office / KDocs via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., WPS --mcp-status, WPS --mcp-page",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("me", help="Show user info (requires auth)")
    sub.add_parser("docs", help="List recent documents (requires auth)")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.WPS.logic.chrome.api import (
        get_auth_state, get_page_info, get_user_info, get_recent_docs,
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

    elif args.command == "me":
        r = get_user_info()
        if r.get("ok"):
            d = r.get("data", {})
            print(f"  Name:   {d.get('name') or '(not visible)'}")
            print(f"  Avatar: {('Yes' if d.get('avatarUrl') else 'No')}")
            ls = d.get("localStorage", {})
            if ls:
                for k, v in list(ls.items())[:5]:
                    print(f"  {k}: {str(v)[:60]}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    elif args.command == "docs":
        r = get_recent_docs()
        if r.get("ok"):
            docs = r.get("docs", [])
            print(f"  Found {r.get('count', 0)} documents")
            for i, d in enumerate(docs):
                print(f"  [{i+1}] {d['name']:<50} {d.get('time','')}")
            if not docs:
                print(f"  {YELLOW}No documents visible — log in first{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
