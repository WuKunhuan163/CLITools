#!/usr/bin/env python3
import sys
import os
from pathlib import Path

def get_file_dialog_bin():
    """Returns the path to the FILEDIALOG binary/script."""
    # Find project root by looking for 'bin' directory
    curr = Path(__file__).resolve().parent
    while curr.parent != curr:
        if (curr / "bin").exists() and (curr / "tool").exists():
            break
        curr = curr.parent
    
    project_root = curr
    bin_path = project_root / "bin" / "FILEDIALOG"
    
    if bin_path.exists():
        return str(bin_path)
    
    # Fallback to main.py
    main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
    if main_py.exists():
        return str(main_py)
        
    # Last resort fallback (historical)
    return str(project_root / "tool" / "FILEDIALOG" / "main.py")
