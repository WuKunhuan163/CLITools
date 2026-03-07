#!/usr/bin/env python3
import sys
import argparse
import json
import subprocess
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
ROOT_PROJECT_ROOT = setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color

class GoogleTool(ToolBase):
    def __init__(self):
        super().__init__("GOOGLE")

    def run(self):
        # Early intercept --mcp-login before argparse
        if "--mcp-login" in sys.argv:
            import importlib.util
            login_path = Path(__file__).resolve().parent / "logic" / "mcp" / "login.py"
            spec = importlib.util.spec_from_file_location("google_mcp_login", str(login_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            as_json_flag = "--json" in sys.argv
            email = None
            rest = [a for a in sys.argv[1:] if a not in ("--mcp-login", "--json", "--no-warning")]
            if rest:
                email = rest[0]
            sys.exit(mod.run_mcp_login(email=email, as_json=as_json_flag))

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
