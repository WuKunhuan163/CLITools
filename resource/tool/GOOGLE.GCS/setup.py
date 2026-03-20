#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.utils import print_success_status

def setup():
    # Standard installation is already handled by the parent tool (GOOGLE) 
    # using ToolEngine. Subtools just need to perform their specific setup here.
    # For GCS, we don't have extra setup steps yet.
    return True

if __name__ == "__main__":
    if setup():
        print_success_status("setup GCS tool")
