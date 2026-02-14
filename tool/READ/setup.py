#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_project_root()
if project_root:
    sys.path.insert(0, str(project_root))

from logic.tool.setup.engine import ToolEngine

def setup():
    tool_name = "READ"
    engine = ToolEngine(tool_name, project_root)
    return engine.install()

if __name__ == "__main__":
    setup()
