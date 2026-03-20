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
    tool = ToolBase("GMAIL")

    parser = argparse.ArgumentParser(
        description="Gmail email client via official Gmail API (OAuth2)",
        epilog=(
            "First-time setup:\n"
            "  1. GMAIL setup   — Configure Google Cloud OAuth credentials\n"
            "  2. GMAIL auth    — Authorize via browser and store tokens\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="Command")

    # --- Session / Auth ---
    sub.add_parser("setup", help="Configure OAuth2 client credentials (one-time)")
    sub.add_parser("auth", help="Run OAuth2 consent flow in browser")
    sub.add_parser("status", help="Check authentication state and profile")
    sub.add_parser("page", help="Show current Gmail tab info (if open)")

    # --- Read ---
    p_inbox = sub.add_parser("inbox", help="List inbox emails")
    p_inbox.add_argument("--limit", type=int, default=20, help="Max emails")

    sub.add_parser("labels", help="List Gmail labels")

    p_search = sub.add_parser("search", help="Search emails")
    p_search.add_argument("query", help="Gmail search query")
    p_search.add_argument("--limit", type=int, default=10, help="Max results")

    p_read = sub.add_parser("read", help="Read a message body")
    p_read.add_argument("msg_id", help="Message ID")

    p_msg = sub.add_parser("message", help="Get message metadata")
    p_msg.add_argument("msg_id", help="Message ID")

    # --- Write ---
    p_send = sub.add_parser("send", help="Send an email")
    p_send.add_argument("to", help="Recipient email address")
    p_send.add_argument("--subject", default="", help="Subject")
    p_send.add_argument("--body", default="", help="Body text")
    p_send.add_argument("--cc", default="", help="CC recipients")
    p_send.add_argument("--bcc", default="", help="BCC recipients")

    p_trash = sub.add_parser("trash", help="Move a message to Trash")
    p_trash.add_argument("msg_id", help="Message ID")

    p_mark_read = sub.add_parser("mark-read", help="Mark a message as read")
    p_mark_read.add_argument("msg_id", help="Message ID")

    p_mark_unread = sub.add_parser("mark-unread", help="Mark a message as unread")
    p_mark_unread.add_argument("msg_id", help="Message ID")

    p_star = sub.add_parser("star", help="Star a message")
    p_star.add_argument("msg_id", help="Message ID")

    p_unstar = sub.add_parser("unstar", help="Unstar a message")
    p_unstar.add_argument("msg_id", help="Message ID")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    # ------------------------------------------------------------------
    # Setup & Auth
    # ------------------------------------------------------------------

    if args.command == "setup":
        from tool.GMAIL.logic.gmail_api import save_credentials, has_credentials
        print(f"\n  {BOLD}Gmail API OAuth2 Setup{RESET}")
        print(f"  {'─' * 40}")
        print(f"  {BLUE}Requirements:{RESET}")
        print(f"    1. Go to https://console.cloud.google.com/")
        print(f"    2. Create a project (or select existing)")
        print(f"    3. Enable the Gmail API")
        print(f"    4. Create OAuth 2.0 credentials (Desktop app)")
        print(f"    5. Copy the Client ID and Client Secret below\n")

        if has_credentials():
            print(f"  {YELLOW}Credentials already configured. Re-entering will overwrite.{RESET}\n")

        client_id = input(f"  Client ID: ").strip()
        client_secret = input(f"  Client Secret: ").strip()

        if not client_id or not client_secret:
            print(f"\n  {RED}Both Client ID and Client Secret are required.{RESET}")
            return

        save_credentials(client_id, client_secret)
        print(f"\n  {GREEN}Credentials saved.{RESET} Now run: {BOLD}GMAIL auth{RESET}")

    elif args.command == "auth":
        from tool.GMAIL.logic.gmail_api import (
            get_auth_url, exchange_code, has_credentials,
        )
        if not has_credentials():
            print(f"  {RED}No credentials configured.{RESET} Run {BOLD}GMAIL setup{RESET} first.")
            return

        auth_url = get_auth_url()
        if not auth_url:
            print(f"  {RED}Failed to generate auth URL.{RESET}")
            return

        print(f"\n  {BOLD}Gmail API Authorization{RESET}")
        print(f"  {'─' * 40}")
        print(f"  {BLUE}Opening browser for consent...{RESET}\n")

        import webbrowser
        webbrowser.open(auth_url)

        print(f"  If the browser didn't open, visit:")
        print(f"  {auth_url}\n")
        print(f"  After approving, paste the authorization code below.\n")

        code = input(f"  Authorization code: ").strip()
        if not code:
            print(f"\n  {RED}No code provided.{RESET}")
            return

        result = exchange_code(code)
        if result.get("ok"):
            print(f"\n  {GREEN}Authenticated successfully!{RESET}")
            print(f"  Tokens stored. You can now use GMAIL commands.")
        else:
            print(f"\n  {RED}Authentication failed:{RESET} {result.get('error', 'Unknown')}")

    # ------------------------------------------------------------------
    # Status & Page Info
    # ------------------------------------------------------------------

    elif args.command == "status":
        from tool.GMAIL.logic.utils.chrome.api import get_auth_state
        r = get_auth_state()
        creds = r.get("credentials_configured", False)
        auth = r.get("authenticated", False)
        tab = r.get("gmail_tab_open", False)
        print(f"  Credentials: {BOLD}{GREEN if creds else RED}{'Configured' if creds else 'Not set'}{RESET}")
        print(f"  Token:       {BOLD}{GREEN if auth else YELLOW}{'Valid' if auth else 'Not authenticated'}{RESET}")
        print(f"  Gmail Tab:   {BOLD}{GREEN if tab else YELLOW}{'Open' if tab else 'Not found'}{RESET}")
        if r.get("email"):
            print(f"  Email:       {r['email']}")
        if not creds:
            print(f"\n  Run {BOLD}GMAIL setup{RESET} to configure OAuth credentials.")
        elif not auth:
            print(f"\n  Run {BOLD}GMAIL auth{RESET} to authorize.")

    elif args.command == "page":
        from tool.GMAIL.logic.utils.chrome.api import get_page_info
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    elif args.command == "inbox":
        from tool.GMAIL.logic.utils.chrome.api import get_inbox
        r = get_inbox(limit=args.limit)
        if r.get("ok"):
            emails = r.get("emails", [])
            print(f"  Showing {r.get('count', 0)} emails\n")
            for i, e in enumerate(emails):
                marker = f"{BOLD}*{RESET}" if e.get("unread") else " "
                star_ch = "★" if e.get("starred") else " "
                sender = e.get("from", "?")[:25]
                subj = e.get("subject", "?")[:45]
                date = e.get("date", "")
                msg_id = e.get("id", "")[:12]
                print(f"  {marker}{star_ch} [{msg_id}] {sender:<25} {subj:<45} {date}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Requires authentication')}")

    elif args.command == "labels":
        from tool.GMAIL.logic.utils.chrome.api import get_labels
        r = get_labels()
        if r.get("ok"):
            labels = r.get("labels", [])
            for lb in labels:
                cnt = f" ({lb['count']})" if lb.get("count") else ""
                print(f"  {lb['name']}{cnt}")
            if not labels:
                print(f"  {YELLOW}No labels found{RESET}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "search":
        from tool.GMAIL.logic.utils.chrome.api import search_emails
        r = search_emails(args.query, limit=args.limit)
        if r.get("ok"):
            emails = r.get("emails", [])
            print(f"  Search '{r.get('query', '')}': {r.get('count', 0)} results\n")
            for i, e in enumerate(emails):
                sender = e.get("from", "?")[:25]
                subj = e.get("subject", "?")[:45]
                date = e.get("date", "")
                msg_id = e.get("id", "")[:12]
                print(f"  [{msg_id}] {sender:<25} {subj:<45} {date}")
            if not emails:
                print(f"  {YELLOW}No results found{RESET}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "read":
        from tool.GMAIL.logic.utils.chrome.api import get_message_body
        r = get_message_body(args.msg_id)
        if r.get("ok"):
            print(f"  {BOLD}From:{RESET}    {r.get('from', '?')}")
            print(f"  {BOLD}Subject:{RESET} {r.get('subject', '?')}")
            print(f"  {BOLD}Date:{RESET}    {r.get('date', '?')}")
            print(f"  {'─' * 50}")
            print(r.get("body", "(empty)"))
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "message":
        from tool.GMAIL.logic.utils.chrome.api import get_message
        r = get_message(args.msg_id)
        if r.get("ok"):
            from tool.GMAIL.logic.gmail_api import _extract_header
            print(f"  {BOLD}ID:{RESET}      {r.get('id', '?')}")
            print(f"  {BOLD}Thread:{RESET}  {r.get('threadId', '?')}")
            print(f"  {BOLD}From:{RESET}    {_extract_header(r, 'From')}")
            print(f"  {BOLD}To:{RESET}      {_extract_header(r, 'To')}")
            print(f"  {BOLD}Subject:{RESET} {_extract_header(r, 'Subject')}")
            print(f"  {BOLD}Date:{RESET}    {_extract_header(r, 'Date')}")
            print(f"  {BOLD}Labels:{RESET}  {', '.join(r.get('labelIds', []))}")
            print(f"  {BOLD}Snippet:{RESET} {r.get('snippet', '')[:100]}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    elif args.command == "send":
        from tool.GMAIL.logic.utils.chrome.api import send_email
        r = send_email(args.to, subject=args.subject, body=args.body,
                       cc=args.cc, bcc=args.bcc)
        if r.get("ok") and r.get("sent"):
            print(f"  {GREEN}Email sent{RESET} to {args.to}")
            if r.get("id"):
                print(f"  Message ID: {r['id']}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Send failed')}")

    elif args.command == "trash":
        from tool.GMAIL.logic.utils.chrome.api import delete_email
        r = delete_email(args.msg_id)
        if r.get("ok") and r.get("deleted"):
            print(f"  {GREEN}Moved to Trash{RESET}: {args.msg_id}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "mark-read":
        from tool.GMAIL.logic.utils.chrome.api import mark_read
        r = mark_read(args.msg_id)
        if r.get("ok"):
            print(f"  {GREEN}Marked as read{RESET}: {args.msg_id}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "mark-unread":
        from tool.GMAIL.logic.utils.chrome.api import mark_unread
        r = mark_unread(args.msg_id)
        if r.get("ok"):
            print(f"  {GREEN}Marked as unread{RESET}: {args.msg_id}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "star":
        from tool.GMAIL.logic.utils.chrome.api import star
        r = star(args.msg_id)
        if r.get("ok"):
            print(f"  {GREEN}Starred{RESET}: {args.msg_id}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    elif args.command == "unstar":
        from tool.GMAIL.logic.utils.chrome.api import unstar
        r = unstar(args.msg_id)
        if r.get("ok"):
            print(f"  {GREEN}Unstarred{RESET}: {args.msg_id}")
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', 'Unknown')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
