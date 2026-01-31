#!/usr/bin/env python3
import sys
from pathlib import Path

def get_file_dialog_bin():
    """Returns the path to the FILEDIALOG binary/script."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    bin_path = project_root / "bin" / "FILEDIALOG"
    if bin_path.exists():
        return str(bin_path)
    return str(project_root / "tool" / "FILEDIALOG" / "main.py")

