#!/usr/bin/env python3
import sys
import subprocess
import os
from pathlib import Path

# Add proj to path so we can import utils
sys.path.append(str(Path(__file__).parent.absolute()))
from proj.utils import get_python_exec

def main():
    python_exec = get_python_exec()
    subprocess.run([python_exec] + sys.argv[1:])

if __name__ == "__main__":
    main()
