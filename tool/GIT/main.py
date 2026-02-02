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
    tool = ToolBase("GIT")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool GIT")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        
        import time
        from logic.turing.display.manager import _get_configured_width, truncate_to_width
        width = _get_configured_width()
        
        for i in range(3, 0, -1):
            msg = f"\r\033[K{BOLD}{BLUE}Progressing{RESET}... {i}s"
            sys.stdout.write(truncate_to_width(msg, width))
            sys.stdout.flush()
            time.sleep(1)
            
        msg = f"\r\033[K{BOLD}{GREEN}Successfully{RESET} finished!\n"
        sys.stdout.write(truncate_to_width(msg, width))
        sys.stdout.flush()
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
