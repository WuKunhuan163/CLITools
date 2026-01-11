#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Use resolve() to get the actual location of the script
script_dir = Path(__file__).resolve().parent
# project_root is two levels up: tool/PYTHON -> tool -> root
project_root = script_dir.parent.parent

# Add the directory containing 'proj' to sys.path for the proxy script itself
sys.path.append(str(script_dir))
from proj.utils import get_python_exec

def main():
    python_exec = get_python_exec()
    
    # Set up environment for the subprocess
    env = os.environ.copy()
    # Add root to PYTHONPATH so tools can find shared 'proj'
    # Add script_dir to PYTHONPATH so it can find its own 'proj'
    python_path = env.get("PYTHONPATH", "")
    new_paths = f"{project_root}:{script_dir}"
    if python_path:
        env["PYTHONPATH"] = f"{new_paths}:{python_path}"
    else:
        env["PYTHONPATH"] = new_paths

    subprocess.run([python_exec] + sys.argv[1:], env=env)

if __name__ == "__main__":
    main()
