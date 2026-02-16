#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) in sys.path:
    sys.path.remove(str(project_root))
sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from tool.GIT.logic.engine import GitEngine
from logic.config import get_color

def main():
    tool = ToolBase("GIT")
    engine = GitEngine(project_root)
    
    parser = argparse.ArgumentParser(description="GIT Tool: A wrapper for Git operations and development branch management.", add_help=False)
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # list-tags
    list_tags_parser = subparsers.add_parser("list-tags", help="List tags from a remote", add_help=False)
    list_tags_parser.add_argument("remote", help="Remote name or URL")

    # fetch-api
    fetch_api_parser = subparsers.add_parser("fetch-api", help="Fetch data from GitHub API", add_help=False)
    fetch_api_parser.add_argument("url", help="GitHub API URL")

    # config-dev
    config_dev_parser = subparsers.add_parser("config-dev", help="Configure designated development branch", add_help=False)
    config_dev_parser.add_argument("branch", help="Branch name to set as designated development branch")

    # commit
    commit_parser = subparsers.add_parser("commit", help="Commit changes with development branch protection", add_help=False)
    commit_parser.add_argument("-m", "--message", required=True, help="Commit message")
    commit_parser.add_argument("--force", action="store_true", help="Force commit even if not on development branch")
    commit_parser.add_argument("--merge", action="store_true", help="Merge current changes into development branch and commit")

    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()

    if args.command == "list-tags":
        tags = engine.list_remote_tags(args.remote)
        for tag in tags: print(tag)
    elif args.command == "fetch-api":
        result = engine.fetch_github_api(args.url)
        import json
        print(json.dumps(result, indent=2))
    elif args.command == "config-dev":
        engine.set_dev_branch(args.branch)
        print(f"{get_color('GREEN')}Designated development branch set to{get_color('RESET')}: {args.branch}")
    elif args.command == "commit":
        dev_branch = engine.get_dev_branch()
        current_branch = engine.get_current_branch()
        
        if dev_branch and current_branch != dev_branch and not args.force:
            if args.merge:
                print(f"{get_color('BLUE')}Merging changes from '{current_branch}' into '{dev_branch}'...{get_color('RESET')}")
                # 1. Switch to dev
                res = engine.run_git(["checkout", dev_branch])
                if res.returncode != 0:
                    print(f"{get_color('RED')}Error{get_color('RESET')}: Failed to checkout '{dev_branch}': {res.stderr}")
                    sys.exit(1)
                # 2. Merge
                res = engine.run_git(["merge", current_branch])
                if res.returncode != 0:
                    print(f"{get_color('RED')}Error{get_color('RESET')}: Merge conflict occurred. Please resolve manually.")
                    sys.exit(1)
                # 3. Commit will happen below
            else:
                print(f"{get_color('RED')}Error{get_color('RESET')}: You are currently on branch '{current_branch}', but the designated development branch is '{dev_branch}'.")
                print(f"Use {get_color('BOLD')}--force{get_color('RESET')} to commit anyway, or {get_color('BOLD')}--merge{get_color('RESET')} to merge and commit on '{dev_branch}'.")
                sys.exit(1)
        
        # Perform commit
        res = engine.run_git(["add", "."])
        res = engine.run_git(["commit", "-m", args.message])
        if res.returncode == 0:
            print(f"{get_color('GREEN')}Successfully committed{get_color('RESET')}: {args.message}")
            # Trigger auto-push if needed (via post-commit hook or manually)
            from logic.git.engine import auto_push_if_needed
            auto_push_if_needed()
        else:
            reason = res.stderr.strip() or res.stdout.strip() or "Unknown reason"
            print(f"{get_color('RED')}Commit failed{get_color('RESET')}: {reason}")
            sys.exit(1)

if __name__ == "__main__":
    main()
