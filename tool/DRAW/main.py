#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

def main():
    tool = ToolBase("DRAW")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool DRAW")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        print(f"{BOLD}{BLUE}Progressing{RESET}... {BOLD}{GREEN}Successfully{RESET} finished!")
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
