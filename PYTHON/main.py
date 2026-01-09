#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Add the directory containing 'proj' to PYTHONPATH for the subprocess
script_dir = Path(__file__).parent.absolute()
env = os.environ.copy()
python_path = env.get("PYTHONPATH", "")
if python_path:
    env["PYTHONPATH"] = f"{script_dir}:{python_path}"
else:
    env["PYTHONPATH"] = str(script_dir)

# Also add to current sys.path for the proxy script itself
sys.path.append(str(script_dir))
from proj.utils import get_python_exec

def main():
    python_exec = get_python_exec()
    subprocess.run([python_exec] + sys.argv[1:], env=env)

if __name__ == "__main__":
    main()
