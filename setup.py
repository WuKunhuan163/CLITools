#!/usr/bin/env python3
import os
import sys
import stat
from pathlib import Path

def setup():
    project_root = Path(__file__).parent.absolute()
    main_py = project_root / "main.py"
    tool_link = project_root / "TOOL"
    
    # 1. Ensure main.py is executable
    if main_py.exists():
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
    else:
        print(f"Error: {main_py} not found. Please create main.py first.")
        sys.exit(1)
        
    # 2. Create TOOL symlink
    if tool_link.exists() or tool_link.is_symlink():
        os.remove(tool_link)
    
    try:
        os.symlink(main_py, tool_link)
        print(f"Successfully created symlink: TOOL -> {main_py}")
    except OSError as e:
        print(f"Error creating symlink: {e}")
        sys.exit(1)

    # 3. Create global data directory
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"Ensured data directory exists: {data_dir}")

if __name__ == "__main__":
    setup()

