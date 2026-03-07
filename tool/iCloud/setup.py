#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
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

from logic.interface.tool import ToolEngine

def setup():
    tool_name = "iCloud"
    engine = ToolEngine(tool_name, project_root)
    return engine.install()

if __name__ == "__main__":
    setup()
