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
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("INTERCOM")

    parser = argparse.ArgumentParser(
        description="Intercom customer messaging via Chrome CDP",
        epilog="MCP commands use --mcp- prefix: e.g., INTERCOM --mcp-status, INTERCOM --mcp-page",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("conversations", help="List recent conversations")
    sub.add_parser("contacts", help="List contacts")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.INTERCOM.logic.utils.chrome.api import (
        get_auth_state, get_page_info, get_conversations, get_contacts,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('pageTitle', '?')}")
        if r.get("isSignUp"):
            print(f"  {YELLOW}Account setup not complete{RESET}")
        if r.get("error"):
            print(f"  {RED}{r['error']}{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            if r.get("heading"):
                print(f"  Heading: {r['heading']}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "conversations":
        r = get_conversations()
        if r.get("ok") and isinstance(r.get("data"), dict):
            convs = r["data"].get("conversations", r["data"])
            if isinstance(convs, list):
                if not convs:
                    print("  (no conversations)")
                for c in convs[:20]:
                    print(f"  {c}")
            else:
                print(f"  {json.dumps(convs)[:300]}")
        else:
            status = r.get("status", "?")
            print(f"{BOLD}{RED}Error{RESET} [{status}]: {r.get('data', 'Requires authenticated session')}")

    elif args.command == "contacts":
        r = get_contacts()
        if r.get("ok") and isinstance(r.get("data"), dict):
            contacts = r["data"].get("contacts", r["data"])
            if isinstance(contacts, list):
                if not contacts:
                    print("  (no contacts)")
                for c in contacts[:20]:
                    print(f"  {c}")
            else:
                print(f"  {json.dumps(contacts)[:300]}")
        else:
            status = r.get("status", "?")
            print(f"{BOLD}{RED}Error{RESET} [{status}]: {r.get('data', 'Requires authenticated session')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
