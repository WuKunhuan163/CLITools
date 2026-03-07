#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse
import json
import subprocess
from pathlib import Path

# Add project root to sys.path
def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent.parent

ROOT_PROJECT_ROOT = find_project_root()
if str(ROOT_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT_PROJECT_ROOT))

from logic.tool.base import ToolBase
from logic.config import get_color

class GoogleTool(ToolBase):
    def __init__(self):
        super().__init__("GOOGLE")

    def run(self):
        parser = argparse.ArgumentParser(description="GOOGLE Tool: Ecosystem Proxy", add_help=False)
        parser.add_argument("command", nargs="?", help="Subcommand to run")
        parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments for the subcommand")
        parser.add_argument("-h", "--help", action="store_true", help="Show this help message")
        
        if self.handle_command_line(parser):
            return

        args = parser.parse_args()

        if args.help or not args.command:
            parser.print_help()
            self.print_rule()
            return

        # Initialize internal modules
        from tool.GOOGLE.logic.engine import GoogleEngine
        engine = GoogleEngine(self.project_root)

        if args.command == "search":
            if not args.args:
                print("Usage: GOOGLE search <query>")
                return
            engine.search(" ".join(args.args))
        elif args.command == "drive":
            if not args.args:
                print("Usage: GOOGLE drive <list|upload|download>")
                return
            subcmd = args.args[0]
            if subcmd == "list":
                engine.drive_list()
            else:
                print(f"Unknown drive command: {subcmd}")
        elif args.command == "trends":
            engine.trends()
        else:
            print(f"Unknown command: {args.command}")
            parser.print_help()

def main():
    tool = GoogleTool()
    tool.run()

if __name__ == "__main__":
    main()
