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
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.blueprint.base import ToolBase
from logic.interface.config import get_color

def main():
    tool = ToolBase("VPN")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool VPN")
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    args, unknown = parser.parse_known_args()
    
    if args.demo:
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        
        import time
        from logic.interface.turing import _get_configured_width, truncate_to_width
        width = _get_configured_width()
        
        for i in range(3, 0, -1):
            msg = f"\r\033[K{BOLD}{BLUE}" + tool.get_translation("label_progressing", "Progressing") + f"{RESET}... {i}s"
            sys.stdout.write(truncate_to_width(msg, width))
            sys.stdout.flush()
            time.sleep(1)
            
        msg = f"\r\033[K{BOLD}{GREEN}" + tool.get_translation("label_successfully_finished", "Successfully") + f"{RESET} " + tool.get_translation("label_finished", "finished!") + "\n"
        sys.stdout.write(truncate_to_width(msg, width))
        sys.stdout.flush()
        return

    print("Hello World!")

if __name__ == "__main__":
    main()
