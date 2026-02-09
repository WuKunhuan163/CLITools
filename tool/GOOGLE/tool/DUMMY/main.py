#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Find project root by looking for bin/TOOL
def find_project_root():
    curr = Path(__file__).resolve().parent
    # Try to find the root by looking for the unique bin/TOOL
    temp = curr
    while temp != temp.parent:
        if (temp / "bin" / "TOOL").exists():
            return temp
        temp = temp.parent
    
    # If not found, look for the first directory that has tool.json AND is NOT named 'DUMMY' or 'SUBSUB' or 'GOOGLE'
    # and its parent is NOT 'tool'
    temp = curr
    while temp != temp.parent:
        if (temp / "tool.json").exists() and temp.parent.name != "tool" and temp.name != "tool":
            return temp
        temp = temp.parent
        
    return Path(__file__).resolve().parent.parent.parent.parent

project_root = find_project_root()
# print(f"DEBUG: DUMMY project_root={project_root}", file=sys.stderr)
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

