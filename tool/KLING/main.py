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
    tool = ToolBase("KLING")

    parser = argparse.ArgumentParser(
        description="Kling AI video generation via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., KLING --mcp-status, KLING --mcp-page",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("me", help="Show user info")
    sub.add_parser("points", help="Show credit points balance")
    sub.add_parser("page", help="Show current page state")
    sub.add_parser("history", help="Show recent generation history from DOM")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.KLING.logic.chrome.api import (
        get_user_info, get_points, get_page_info, get_generation_history,
    )

    if args.command == "me":
        r = get_user_info()
        if r.get("ok"):
            d = r["data"]
            print(f"  User ID:  {d.get('userId', '?')}")
            print(f"  Username: {d.get('userName', '?')}")
            print(f"  Email:    {d.get('email', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "points":
        r = get_points()
        if r.get("ok"):
            d = r["data"]
            pts = d.get("points")
            print(f"  Points: {pts if pts else '(not visible)'}")
            if d.get("plan"):
                print(f"  Plan:   {d['plan']}")
            if r.get("note"):
                print(f"  {YELLOW}{r['note']}{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title: {r.get('title', '?')}")
            print(f"  URL:   {r.get('url', '?')}")
            if r.get("activePage"):
                print(f"  Page:  {r['activePage']}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "history":
        r = get_generation_history()
        if r.get("ok"):
            items = r.get("items", [])
            print(f"  Found {r.get('count', 0)} items")
            for i, item in enumerate(items):
                media = "video" if item.get("hasVideo") else ("image" if item.get("hasImage") else "?")
                print(f"  [{i+1}] [{media}] {item.get('text', '')[:80]}")
            if not items:
                print("  (no items visible — navigate to Assets page first)")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
