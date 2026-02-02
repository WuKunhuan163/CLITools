#!/usr/bin/env python3
import sys
import argparse
import subprocess
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from tool.GIT.logic.engine import GitEngine

def main():
    parser = argparse.ArgumentParser(description="GIT Tool: A wrapper for Git operations and GitHub API.", add_help=False)
    parser.add_argument("--git-list-tags", help="List tags from a remote")
    parser.add_argument("--git-fetch-api", help="Fetch data from GitHub API")
    parser.add_argument("-h", "--help", action="store_true", help="Show this help message")

    args, unknown = parser.parse_known_args()

    engine = GitEngine()

    if args.help:
        parser.print_help()
        print("\nAll other arguments will be passed to the system git command.")
        return

    if args.git_list_tags:
        tags = engine.list_remote_tags(args.git_list_tags)
        for tag in tags:
            print(tag)
        return

    if args.git_fetch_api:
        result = engine.fetch_github_api(args.git_fetch_api)
        import json
        print(json.dumps(result, indent=2))
        return

    # Forward to system git
    # Use /usr/bin/git to avoid recursion if bin/ is in PATH
    cmd = ["/usr/bin/git"] + unknown
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:
        print(f"Error executing git: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
