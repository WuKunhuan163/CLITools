#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Get the directory of this script
script_dir = Path(__file__).parent.absolute()
# Path to the standalone python executable
python_exec = script_dir / "proj" / "python3.10.19" / "install" / "bin" / "python3"

if not python_exec.exists():
    # Fallback to system python if standalone is missing
    python_exec = "python3"

subprocess.run([str(python_exec)] + sys.argv[1:])
