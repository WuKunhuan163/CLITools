#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Find project root by looking for bin/TOOL
def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    # Fallback to a fixed number of parents if bin/TOOL not found
    return Path(__file__).resolve().parent.parent.parent.parent

project_root = find_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase

class DummySubtool(ToolBase):
    def __init__(self):
        super().__init__("DUMMY")

    def run(self):
        print("Hello from DUMMY subtool of GOOGLE!")

def main():
    tool = DummySubtool()
    if tool.handle_command_line():
        return
    tool.run()

if __name__ == "__main__":
    main()
