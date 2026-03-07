#!/usr/bin/env python3
"""
GITHUB Tool - GitHub integration via GitHub MCP
MCP-based integration wrapping @modelcontextprotocol/server-github.
"""
import os
import sys
import json
import argparse
from pathlib import Path

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
root_str = str(project_root)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

from logic.interface.tool import ToolBase
from logic.interface.config import get_color

BOLD = get_color("BOLD")
GREEN = get_color("GREEN")
RED = get_color("RED")
BLUE = get_color("BLUE")
YELLOW = get_color("YELLOW")
RESET = get_color("RESET")


class GITHUBTool(ToolBase):
    def __init__(self):
        super().__init__("GITHUB")

    def get_config_value(self, key):
        """Retrieve a config value from data/config.json."""
        config_file = self.script_dir / "data" / "config.json"
        if config_file.exists():
            try:
                with open(config_file) as f:
                    return json.load(f).get(key)
            except Exception:
                pass
        return None

    def set_config_value(self, key, value):
        """Store a config value in data/config.json."""
        config_file = self.script_dir / "data" / "config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config = {}
        if config_file.exists():
            try:
                with open(config_file) as f:
                    config = json.load(f)
            except Exception:
                pass
        config[key] = value
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)


def main():
    tool = GITHUBTool()

    parser = argparse.ArgumentParser(description="GitHub integration via GitHub MCP", add_help=False)
    parser.add_argument("command", nargs="?", help="Command to run")
    parser.add_argument("args", nargs="*", help="Additional arguments")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    if tool.handle_command_line(parser):
        return

    args, unknown = parser.parse_known_args()

    if args.command == "status":
        print(f"{BOLD}GITHUB{RESET} tool status:")
        print(f"  MCP package: @modelcontextprotocol/server-github")
        print(f"  Type: npm")
        print(f"  Capabilities: repositories, issues, pull-requests, code-search, file-operations")
        return 0

    if args.command == "config":
        if not args.args or len(args.args) < 2:
            print(f"Usage: GITHUB config <key> <value>")
            return 1
        key, value = args.args[0], args.args[1]
        tool.set_config_value(key, value)
        print(f"{BOLD}{GREEN}Successfully set{RESET} {key}.")
        return 0

    parser.print_help()
    print(f"\n{BOLD}Capabilities{RESET}: repositories, issues, pull-requests, code-search, file-operations")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
