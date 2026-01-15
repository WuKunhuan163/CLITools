#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def main():
    project_root = Path(__file__).resolve().parent.parent.parent
    python_bin = project_root / "bin" / "PYTHON"
    
    if not python_bin.exists():
        print("Error: PYTHON tool not found. Please install it first.")
        sys.exit(1)
        
    print("USERINPUT setup: requesting Python 3.10.19...")
    try:
        # Call the PYTHON tool to install 3.10.19
        subprocess.run([str(python_bin), "--py-install", "python3.10.19"], check=True)
        print("Python 3.10.19 installed successfully for USERINPUT.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to install Python 3.10.19: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()





