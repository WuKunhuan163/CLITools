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

from interface.tool import MCPToolBase
from interface.config import get_color


def main():
    tool = MCPToolBase("YUQUE", session_name="yuque")

    parser = argparse.ArgumentParser(
        description="Yuque knowledge base via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., YUQUE --mcp-boot",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand")

    sub.add_parser("boot", help="Boot Yuque CDMCP session")
    sub.add_parser("status", help="Check current page state")
    sub.add_parser("page", help="Get detailed page info")
    sub.add_parser("scan", help="Scan page for interactive elements")
    sub.add_parser("session", help="Show CDMCP session status")
    sub.add_parser("state", help="Get comprehensive MCP state")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.YUQUE.logic.utils.chrome.api import (
        boot_session, get_status, get_page_info, scan_elements,
    )

    if args.command == "boot":
        r = boot_session()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Booted{RESET} Yuque session.")
            print(f"  Action: {r.get('action', '?')}")
            if r.get("url"):
                print(f"  URL: {r['url']}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET} to boot: {r.get('error', '?')}")

    elif args.command == "status":
        r = get_status()
        if r.get("ok"):
            print(f"  {BOLD}Page{RESET}: {r.get('title', '?')}")
            print(f"  URL: {r.get('url', '?')}")
            if r.get("logged_in") is not None:
                print(f"  Logged in: {r['logged_in']}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title: {r.get('title', '?')}")
            print(f"  Path: {r.get('path', '?')}")
            btns = r.get("buttons", [])
            if btns:
                print(f"  Buttons ({len(btns)}):")
                for b in btns[:10]:
                    print(f"    - {b}")
            headings = r.get("headings", [])
            if headings:
                print(f"  Headings ({len(headings)}):")
                for h in headings[:10]:
                    print(f"    - {h}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "scan":
        r = scan_elements()
        if r.get("ok"):
            elements = r.get("elements", [])
            print(f"  Found {r.get('count', 0)} interactive elements:")
            for el in elements:
                tag = el.get("tag", "?")
                etype = el.get("type", "")
                text = el.get("text", "")[:40]
                rect = el.get("rect", {})
                pos = f"({rect.get('x',0)},{rect.get('y',0)})"
                print(f"    <{tag}> {etype:10s} {pos:12s} {text}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "session" or args.command == "state":
        tool.print_mcp_state()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
