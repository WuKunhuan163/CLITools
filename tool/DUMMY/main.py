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
    tool = ToolBase("DUMMY")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool DUMMY")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        BLUE = get_color("BLUE", "\033[34m")
        RESET = get_color("RESET", "\033[0m")
        
        import time
        from logic.turing.display.manager import _get_configured_width, truncate_to_width
        width = _get_configured_width()
        
        for i in range(3, 0, -1):
            msg = f"{BOLD}{BLUE}Progressing{RESET}... {i}s"
            sys.stdout.write(f"\r\033[K{truncate_to_width(msg, width)}")
            sys.stdout.flush()
            time.sleep(1)
            
        sys.stdout.write("\r\033[K") # Final erasure
        success_msg = f"{BOLD}{GREEN}Successfully{RESET} finished!"
        sys.stdout.write(f"{truncate_to_width(success_msg, width)}\n")
        sys.stdout.flush()
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
