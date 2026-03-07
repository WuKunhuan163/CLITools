#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
from pathlib import Path

# tool/iCloud.iCloudPD/setup.py -> project root
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path:
        sys.path.remove(root_str)
    sys.path.insert(0, root_str)
else:
    # Fallback
    project_root = Path(__file__).resolve().parent.parent.parent
    sys.path.insert(0, str(project_root))

from interface.tool import ToolEngine

def setup():
    # Standard installation (dependencies, shortcut) is handled by ToolEngine.
    return True

if __name__ == "__main__":
    setup()
