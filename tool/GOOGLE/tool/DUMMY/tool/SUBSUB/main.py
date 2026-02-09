#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Robust project root detection
def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return Path(__file__).resolve().parent.parent.parent.parent.parent.parent

project_root = find_project_root()
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase

class SubSubtool(ToolBase):
    def __init__(self):
        super().__init__("SUBSUB")

    def run(self):
        print("Hello from SUBSUB sub-subtool of DUMMY!")

def main():
    tool = SubSubtool()
    if tool.handle_command_line():
        return
    tool.run()

if __name__ == "__main__":
    main()
