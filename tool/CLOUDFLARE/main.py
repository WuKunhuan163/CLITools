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
    tool = ToolBase("CLOUDFLARE")

    parser = argparse.ArgumentParser(
        description="Cloudflare management via Chrome CDP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("user", help="Show authenticated user info")
    sub.add_parser("account", help="Show account info")

    z_p = sub.add_parser("zones", help="List DNS zones")
    z_p.add_argument("--limit", type=int, default=20, help="Max results")

    dns_p = sub.add_parser("dns", help="List DNS records for a zone")
    dns_p.add_argument("zone_id", help="Zone ID")
    dns_p.add_argument("--limit", type=int, default=50, help="Max results")

    sub.add_parser("workers", help="List Workers scripts")
    sub.add_parser("pages", help="List Pages projects")
    sub.add_parser("kv", help="List KV namespaces")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.CLOUDFLARE.logic.chrome.api import (
        get_user, get_account, list_zones, list_dns_records,
        list_workers, list_pages_projects, list_kv_namespaces,
    )

    def _err(data):
        errors = data.get("errors", [])
        return errors[0].get("message", "Unknown error") if errors else "Unknown error"

    if args.command == "user":
        r = get_user()
        if r.get("success"):
            u = r["result"]
            print(f"  Email:    {u.get('email', '?')}")
            print(f"  Username: {u.get('username', '?')}")
            print(f"  Name:     {u.get('first_name', '')} {u.get('last_name', '')}")
            print(f"  2FA:      {u.get('two_factor_authentication_enabled', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "account":
        r = get_account()
        if r.get("success"):
            a = r["result"]
            print(f"  Name: {a.get('name', '?')}")
            print(f"  ID:   {a.get('id', '?')}")
            print(f"  Type: {a.get('type', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "zones":
        r = list_zones(per_page=args.limit)
        if r.get("success"):
            zones = r.get("result", [])
            if not zones:
                print("  (no zones)")
            for z in zones:
                status = z.get("status", "?")
                print(f"  {z['name']:<40} {status:<12} {z.get('id', '')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "dns":
        r = list_dns_records(args.zone_id, per_page=args.limit)
        if r.get("success"):
            records = r.get("result", [])
            if not records:
                print("  (no records)")
            for rec in records:
                print(f"  {rec.get('type','?'):<8} {rec.get('name','?'):<40} {rec.get('content',''):<40} TTL={rec.get('ttl','?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "workers":
        r = list_workers()
        if r.get("success"):
            scripts = r.get("result", [])
            if not scripts:
                print("  (no workers)")
            for s in scripts:
                print(f"  {s.get('id', '?'):<40} modified: {s.get('modified_on', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "pages":
        r = list_pages_projects()
        if r.get("success"):
            projects = r.get("result", [])
            if not projects:
                print("  (no pages projects)")
            for p in projects:
                print(f"  {p.get('name', '?'):<30} {p.get('subdomain', '')}.pages.dev")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "kv":
        r = list_kv_namespaces()
        if r.get("success"):
            nss = r.get("result", [])
            if not nss:
                print("  (no KV namespaces)")
            for ns in nss:
                print(f"  {ns.get('title', '?'):<40} {ns.get('id', '')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
