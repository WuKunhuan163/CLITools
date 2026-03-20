#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from logic.config import get_color

def main():
    tool = ToolBase("CLIANYTHING")
    
    parser = argparse.ArgumentParser(description="Tool CLIANYTHING", add_help=False)
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
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
