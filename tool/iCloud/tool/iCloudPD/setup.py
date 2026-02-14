#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.setup.engine import ToolEngine

def setup():
    tool_name = "iCloudPD"
    parent_tool_dir = project_root / "tool" / "iCloud" / "tool"
    engine = ToolEngine(tool_name, project_root, parent_tool_dir=parent_tool_dir)
    
    # Manually run the necessary steps instead of the full install() which might rmtree
    print(f"Setting up {tool_name}...")
    if engine.handle_pip_deps():
        if engine.create_shortcut():
            from logic.utils import print_success_status
            print_success_status(f"set up {tool_name}")
            return True
    return False

if __name__ == "__main__":
    setup()
