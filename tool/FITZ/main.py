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
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.blueprint.base import ToolBase

def main():
    tool = ToolBase("FITZ")
    
    parser = argparse.ArgumentParser(description="Tool FITZ", add_help=False)
    parser.add_argument("--demo", action="store_true", help="Showcase colors and workers")
    
    if tool.handle_command_line(parser): return
    
    args = parser.parse_args()
    
    if args.demo:
        # ... demo logic ...
        return

    import fitz
    fitz.TOOLS.mupdf_display_errors(False)
    print("FITZ tool active.")

if __name__ == "__main__":
    main()
