#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Universal path resolver bootstrap
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
    tool = ToolBase("GOOGLE.GD")

    parser = argparse.ArgumentParser(
        description="Google Drive operations via CDP", add_help=False
    )
    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # GOOGLE.GD list <folder_id>
    ls_p = subparsers.add_parser("list", help="List files in a Drive folder")
    ls_p.add_argument("folder_id", help="Drive folder ID")
    ls_p.add_argument("--query", default="", help="Extra query filter")
    ls_p.add_argument("--limit", type=int, default=20, help="Max results")

    # GOOGLE.GD create <name> --type <type> --folder <id>
    cr_p = subparsers.add_parser("create", help="Create a Drive file")
    cr_p.add_argument("name", help="File name")
    cr_p.add_argument("--type", default="colab", help="File type (colab, doc, sheet, ...)")
    cr_p.add_argument("--folder", required=True, help="Parent folder ID")
    cr_p.add_argument("--content", default="", help="File content")

    # GOOGLE.GD delete <file_id>
    del_p = subparsers.add_parser("delete", help="Delete a Drive file")
    del_p.add_argument("file_id", help="File ID to delete")

    # GOOGLE.GD about
    subparsers.add_parser("about", help="Show Drive user and quota info")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.GOOGLE.interface.main import (
        list_drive_files, create_drive_file, delete_drive_file, get_drive_about,
    )

    if args.command == "list":
        result = list_drive_files(args.folder_id, query=args.query, page_size=args.limit)
        if result.get("success"):
            files = result.get("files", [])
            if not files:
                print("(empty)")
            for f in files:
                size = f.get("size", "-")
                print(f"  {f['name']:<40} {f.get('mimeType',''):<45} {size}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {result.get('error')}")

    elif args.command == "create":
        result = create_drive_file(args.name, args.type, args.folder, content=args.content)
        if result.get("success"):
            print(f"{BOLD}{GREEN}Created{RESET}: {result.get('name')} ({result.get('id', result.get('file_id'))})")
            link = result.get("link") or result.get("colab_url", "")
            if link:
                print(f"  {link}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {result.get('error')}")

    elif args.command == "delete":
        ok = delete_drive_file(args.file_id)
        if ok:
            print(f"{BOLD}{GREEN}Deleted{RESET}: {args.file_id}")
        else:
            print(f"{BOLD}{RED}Failed{RESET} to delete {args.file_id}")

    elif args.command == "about":
        result = get_drive_about()
        if result.get("success"):
            data = result.get("data", {})
            user = data.get("user", {})
            quota = data.get("storageQuota", {})
            print(f"  User: {user.get('displayName', '?')} ({user.get('emailAddress', '?')})")
            usage = int(quota.get("usage", 0)) / (1024**3)
            limit = int(quota.get("limit", 0)) / (1024**3)
            print(f"  Storage: {usage:.2f} GB / {limit:.2f} GB")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {result.get('error')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
