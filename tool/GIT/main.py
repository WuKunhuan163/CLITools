#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from tool.GIT.logic.engine import GitEngine

def main():
    tool = ToolBase("GIT")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="GIT Tool: A wrapper for Git operations and GitHub API.", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # list-tags
    list_tags_parser = subparsers.add_parser("list-tags", help="List tags from a remote", add_help=False)
    list_tags_parser.add_argument("remote", help="Remote name or URL")

    # fetch-api
    fetch_api_parser = subparsers.add_parser("fetch-api", help="Fetch data from GitHub API", add_help=False)
    fetch_api_parser.add_argument("url", help="GitHub API URL")

    # Only parse if the first argument is one of our commands
    if len(sys.argv) > 1 and sys.argv[1] in ["list-tags", "fetch-api", "setup", "rule"]:
        try:
            # Re-enable help for our specific commands if needed, 
            # but actually ToolBase handles setup and rule.
            args, unknown = parser.parse_known_args()
        except:
            args = None
    else:
        args = None

    if args and args.command == "list-tags":
        engine = GitEngine()
        tags = engine.list_remote_tags(args.remote)
        for tag in tags:
            print(tag)
    elif args and args.command == "fetch-api":
        engine = GitEngine()
        result = engine.fetch_github_api(args.url)
        import json
        print(json.dumps(result, indent=2))
    else:
        # Pass unknown command to system git
        import subprocess
        cmd = ["/usr/bin/git"] + sys.argv[1:]
        try:
            res = subprocess.run(cmd)
            sys.exit(res.returncode)
        except Exception as e:
            print(f"Error executing system git: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
