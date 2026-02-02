#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def test_python_proxy():
    """Test if PYTHON tool correctly forwards commands to python executable."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    python_bin = project_root / "bin" / "PYTHON"
    
    if not python_bin.exists():
        print(f"Error: PYTHON binary not found at {python_bin}")
        return False

    # Test 'python --version'
    result = subprocess.run([str(python_bin), "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: 'PYTHON --version' failed with code {result.returncode}")
        print(f"Stderr: {result.stderr}")
        return False
    
    print(f"Success: 'PYTHON --version' returned: {result.stdout.strip() or result.stderr.strip()}")
    
    # Test 'python -c "print(1+1)"'
    result = subprocess.run([str(python_bin), "-c", "print(1+1)"], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: 'PYTHON -c' failed with code {result.returncode}")
        return False
    
    if result.stdout.strip() != "2":
        print(f"Error: Expected '2', got '{result.stdout.strip()}'")
        return False
    
    print("Success: 'PYTHON -c' correctly executed python code.")
    return True

if __name__ == "__main__":
    if test_python_proxy():
        print("\nOverall Status: PASS")
        sys.exit(0)
    else:
        print("\nOverall Status: FAIL")
        sys.exit(1)

