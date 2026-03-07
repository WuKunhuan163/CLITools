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
from interface.config import get_color


def main():
    tool = ToolBase("ATLASSIAN")

    parser = argparse.ArgumentParser(
        description="Atlassian account management via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("me", help="Show authenticated user profile")

    notif_p = sub.add_parser("notifications", help="Show recent notifications")
    notif_p.add_argument("--limit", type=int, default=10, help="Max notifications")

    sub.add_parser("preferences", help="Show user preferences (locale, timezone)")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.ATLASSIAN.logic.chrome.api import (
        get_me, get_notifications, get_user_preferences,
    )

    if args.command == "me":
        r = get_me()
        if r.get("ok") and isinstance(r.get("data"), dict):
            d = r["data"]
            print(f"  Name:     {d.get('name', '?')}")
            print(f"  Email:    {d.get('email', '?')}")
            print(f"  Nickname: {d.get('nickname', '?')}")
            print(f"  Locale:   {d.get('locale', '?')}")
            print(f"  Status:   {d.get('account_status', '?')}")
            print(f"  Type:     {d.get('account_type', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('data', 'Unknown error')}")

    elif args.command == "notifications":
        r = get_notifications(max_count=args.limit)
        if r.get("ok") and isinstance(r.get("data"), dict):
            items = r["data"].get("data", [])
            has_unread = r["data"].get("hasUnread", False)
            print(f"  Unread: {has_unread}")
            if not items:
                print("  (no notifications)")
            for item in items:
                print(f"  - {item}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('data', 'Unknown error')}")

    elif args.command == "preferences":
        r = get_user_preferences()
        if r.get("ok") and isinstance(r.get("data"), dict):
            d = r["data"]
            for k, v in d.items():
                if v is not None:
                    print(f"  {k:<20} {v}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('data', 'Unknown error')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
