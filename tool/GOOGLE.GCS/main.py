#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# tool/GOOGLE/tool/GCS/main.py -> 6 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

def main():
    # GCS is a subtool of GOOGLE, using the flat namespace naming convention.
    tool = ToolBase("GOOGLE.GCS")
    
    parser = argparse.ArgumentParser(description="Google Drive Remote Controller (GCS)", add_help=False)
    parser.add_argument("command", nargs="?", help="Subcommand (ls, cat, etc.)")
    parser.add_argument("--folder-id", help="Target Google Drive folder ID")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return

    print(f"GCS executing command: {args.command}")

if __name__ == "__main__":
    main()
