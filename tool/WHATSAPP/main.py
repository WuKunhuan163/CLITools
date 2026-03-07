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
    tool = ToolBase("WHATSAPP")

    parser = argparse.ArgumentParser(
        description="WhatsApp Web messaging via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., WHATSAPP --mcp-status, WHATSAPP --mcp-send",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("status", help="Check link/authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("chats", help="List visible chats (requires linked session)")
    sub.add_parser("profile", help="Show profile info (requires linked session)")
    p_search = sub.add_parser("search", help="Search contacts/chats")
    p_search.add_argument("query", help="Name or number to search")
    p_send = sub.add_parser("send", help="Send a message to a phone number")
    p_send.add_argument("phone", help="Phone number (e.g. +85290549853)")
    p_send.add_argument("message", help="Message text to send")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.WHATSAPP.logic.chrome.api import (
        get_auth_state, get_page_info, get_chats, get_profile,
        search_contact, send_message,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Linked: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")
        if r.get("needsQrScan"):
            print(f"  {YELLOW}Scan QR code with phone to link{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title: {r.get('title', '?')}")
            print(f"  URL:   {r.get('url', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "chats":
        r = get_chats()
        if r.get("ok"):
            chats = r.get("chats", [])
            print(f"  Found {r.get('count', 0)} chats")
            for i, c in enumerate(chats):
                unread = f" [{c['unread']}]" if c.get("unread") else ""
                print(f"  [{i+1}] {c['name']:<25} {c.get('time',''):<10} {c.get('lastMessage','')[:40]}{unread}")
            if not chats:
                print(f"  {YELLOW}No chats visible — scan QR to link first{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires linked session')}")

    elif args.command == "profile":
        r = get_profile()
        if r.get("ok"):
            d = r.get("data", {})
            print(f"  Name:   {d.get('pushName') or '(not available)'}")
            print(f"  Avatar: {('Yes' if d.get('avatarUrl') else 'No')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires linked session')}")

    elif args.command == "search":
        r = search_contact(args.query)
        if r.get("ok"):
            contacts = r.get("contacts", [])
            print(f"  Found {r.get('count', 0)} results for '{args.query}'")
            for i, c in enumerate(contacts):
                print(f"  [{i+1}] {c['name']}")
            if not contacts:
                print(f"  {YELLOW}No matching contacts{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "send":
        r = send_message(args.phone, args.message)
        if r.get("ok"):
            if r.get("sent"):
                print(f"  {BOLD}{GREEN}Successfully sent{RESET} message to {args.phone}.")
            else:
                print(f"  {YELLOW}Message may not have been sent{RESET}")
                if r.get("lastOutgoing"):
                    print(f"  Last outgoing: {r['lastOutgoing'][:60]}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")
            if r.get("page"):
                print(f"  Page: {r['page'][:100]}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
