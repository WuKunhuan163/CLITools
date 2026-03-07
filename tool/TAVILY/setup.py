#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.interface.tool import ToolEngine
from logic.utils import print_success_status

def setup():
    tool_name = "TAVILY"
    engine = ToolEngine(tool_name, project_root)
    
    # 1. Standard installation (dependencies + shortcut)
    return engine.install()

if __name__ == "__main__":
    setup()
