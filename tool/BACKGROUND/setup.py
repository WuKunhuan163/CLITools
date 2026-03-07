#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import os
import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

from logic.interface.tool import ToolEngine

def setup():
    tool_name = "BACKGROUND"
    engine = ToolEngine(tool_name, project_root)
    
    if engine.handle_pip_deps():
        if engine.create_shortcut():
            return True
    return False

if __name__ == "__main__":
    setup()

