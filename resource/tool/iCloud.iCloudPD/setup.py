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

from logic.setup.engine import ToolEngine

def setup():
    tool_name = "iCloudPD"
    # iCloudPD is a subtool of iCloud
    parent_tool_dir = project_root / "tool" / "iCloud" / "tool"
    engine = ToolEngine(tool_name, project_root, parent_tool_dir=parent_tool_dir)
    
    # 1. Pip Dependencies
    if engine.handle_pip_deps():
        # 2. Entry Point
        if engine.create_shortcut():
            from logic.utils import print_success_status
            print_success_status(f"setup {tool_name} tool")
            return True
    return False

if __name__ == "__main__":
    setup()
