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
    tool = ToolBase("SENTRY")

    parser = argparse.ArgumentParser(
        description="Sentry error monitoring via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("orgs", help="List organizations (requires auth)")
    p_proj = sub.add_parser("projects", help="List projects (requires auth)")
    p_proj.add_argument("org", help="Organization slug")
    p_iss = sub.add_parser("issues", help="List issues (requires auth)")
    p_iss.add_argument("org", help="Organization slug")
    p_iss.add_argument("--project", help="Project slug filter")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.SENTRY.logic.chrome.api import (
        get_auth_state, get_page_info, get_organizations, get_projects, get_issues,
    )

    if args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")
        if r.get("isLogin"):
            print(f"  {YELLOW}On login page{RESET}")
        if r.get("isSetup"):
            print(f"  {YELLOW}On setup/identity page{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            if r.get("heading"):
                print(f"  Heading: {r['heading']}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Unknown')}")

    elif args.command == "orgs":
        r = get_organizations()
        if r.get("ok") and isinstance(r.get("data"), list):
            orgs = r["data"]
            if not orgs:
                print(f"  {YELLOW}No organizations{RESET}")
            for o in orgs:
                print(f"  {o.get('name', '?'):<30} slug={o.get('slug', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    elif args.command == "projects":
        r = get_projects(args.org)
        if r.get("ok") and isinstance(r.get("data"), list):
            projects = r["data"]
            if not projects:
                print(f"  {YELLOW}No projects{RESET}")
            for p in projects:
                print(f"  {p.get('name', '?'):<30} slug={p.get('slug', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    elif args.command == "issues":
        r = get_issues(args.org, project_slug=getattr(args, "project", None))
        if r.get("ok") and isinstance(r.get("data"), list):
            issues = r["data"]
            if not issues:
                print(f"  {YELLOW}No issues{RESET}")
            for iss in issues[:20]:
                print(f"  [{iss.get('shortId', '?')}] {iss.get('title', '?')[:70]}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {r.get('error', 'Requires authenticated session')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
