#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
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
    tool.run()

if __name__ == "__main__":
    main()

