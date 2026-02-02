#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tool.GIT.logic.engine import GitEngine

def main():
    parser = argparse.ArgumentParser(description="GIT Tool: A wrapper for Git operations and GitHub API.")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # list-tags
    list_tags_parser = subparsers.add_parser("list-tags", help="List tags from a remote")
    list_tags_parser.add_argument("remote", help="Remote name or URL")

    # fetch-api
    fetch_api_parser = subparsers.add_parser("fetch-api", help="Fetch data from GitHub API")
    fetch_api_parser.add_argument("url", help="GitHub API URL")

    args = parser.parse_args()

    engine = GitEngine()

    if args.command == "list-tags":
        tags = engine.list_remote_tags(args.remote)
        for tag in tags:
            print(tag)
    elif args.command == "fetch-api":
        result = engine.fetch_github_api(args.url)
        import json
        print(json.dumps(result, indent=2))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
