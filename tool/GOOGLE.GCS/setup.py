#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
from pathlib import Path

# tool/GOOGLE.GCS/setup.py -> 2 levels up to project root
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from interface.utils import print_success_status

def setup():
    # Standard installation (dependencies, shortcut) is handled by ToolEngine.
    # GCS currently has no extra custom setup steps.
    return True

if __name__ == "__main__":
    if setup():
        print_success_status("setup GOOGLE.GCS tool")
