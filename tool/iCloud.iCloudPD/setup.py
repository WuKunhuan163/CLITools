#!/usr/bin/env python3
import sys
from pathlib import Path

# tool/iCloud.iCloudPD/setup.py -> 2 levels up to project root
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.utils import print_success_status

def setup():
    # Standard installation (dependencies, shortcut) is handled by ToolEngine.
    # iCloud.iCloudPD has its main logic in main.py.
    return True

if __name__ == "__main__":
    if setup():
        print_success_status("setup iCloud.iCloudPD tool")
