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
    tool = ToolBase("GMAIL")

    parser = argparse.ArgumentParser(
        description="Gmail email client via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check authentication state and unread count")
    sub.add_parser("page", help="Show current page info")
    p_inbox = sub.add_parser("inbox", help="List inbox emails (requires auth)")
    p_inbox.add_argument("--limit", type=int, default=20, help="Max emails to show")
    sub.add_parser("labels", help="List sidebar labels (requires auth)")
    p_search = sub.add_parser("search", help="Search emails (requires auth)")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")
    p_send = sub.add_parser("send", help="Compose and send an email (requires auth)")
    p_send.add_argument("to", help="Recipient email address")
    p_send.add_argument("--subject", default="", help="Email subject")
    p_send.add_argument("--body", default="", help="Email body text")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.GMAIL.logic.chrome.api import (
        get_auth_state, get_page_info, get_inbox, get_labels, search_emails,
        send_email,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        if r.get("email"):
            print(f"  Email:   {r['email']}")
        if r.get("unreadCount") is not None:
            print(f"  Unread:  {r['unreadCount']}")
        print(f"  Page:    {r.get('title', '?')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "inbox":
        r = get_inbox(limit=args.limit)
        if r.get("ok"):
            emails = r.get("emails", [])
            print(f"  Showing {r.get('count', 0)} emails")
            for i, e in enumerate(emails):
                marker = f"{BOLD}*{RESET}" if e.get("unread") else " "
                star = "★" if e.get("starred") else " "
                print(f"  {marker}{star} [{i+1:2d}] {e['from'][:20]:<20} {e['subject'][:45]:<45} {e.get('date','')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    elif args.command == "labels":
        r = get_labels()
        if r.get("ok"):
            labels = r.get("labels", [])
            for lb in labels:
                cnt = f" ({lb['count']})" if lb.get("count") else ""
                print(f"  {lb['name']}{cnt}")
            if not labels:
                print(f"  {YELLOW}No labels visible{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "search":
        r = search_emails(args.query, limit=args.limit)
        if r.get("ok"):
            emails = r.get("emails", [])
            print(f"  Search '{r.get('query','')}': {r.get('count', 0)} results")
            for i, e in enumerate(emails):
                print(f"  [{i+1:2d}] {e['from'][:20]:<20} {e['subject'][:45]:<45} {e.get('date','')}")
            if not emails:
                print(f"  {YELLOW}No results found{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "send":
        r = send_email(args.to, subject=args.subject, body=args.body)
        if r.get("ok") and r.get("sent"):
            print(f"  {BOLD}{GREEN}Successfully sent{RESET} email to {args.to}.")
        elif r.get("ok"):
            print(f"  {YELLOW}Email may not have been sent{RESET}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
