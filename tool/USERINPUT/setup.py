#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Setup Tool")
    parser.add_argument("--version", default="python3.10.19", help="Python version to install (default: python3.10.19)")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent.parent
    python_bin = project_root / "bin" / "PYTHON"
    
    if not python_bin.exists():
        print("Error: PYTHON tool binary not found at " + str(python_bin))
        print("Please install it first using: TOOL install PYTHON")
        sys.exit(1)
        
    version = args.version
    if not version.startswith("python"):
        version = f"python{version}"

    # Auto-detect platform tag if needed
    if "-" not in version:
        system = platform.system().lower()
        if system == "darwin":
            # For macOS, check arch
            arch = platform.machine().lower()
            if "arm" in arch or "aarch64" in arch:
                version = f"{version}-macos-arm64"
            else:
                version = f"{version}-macos"
        elif system == "linux":
            version = f"{version}-linux64"
        elif system == "windows":
            version = f"{version}-windows-amd64"

    print(f"USERINPUT setup: requesting {version}...")
    try:
        # Call the PYTHON tool to install the specific version
        # Use --py-install which is the correct flag for the PYTHON tool
        cmd = [str(python_bin), "--py-install", version]
        print(f"Running: {' '.join(cmd)}")
        # Use run with check=True to raise error on failure
        result = subprocess.run(cmd, check=False) # check=False because we want to see output
        
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd)
            
        print(f"\n{version} installed successfully for USERINPUT.")
    except subprocess.CalledProcessError as e:
        print(f"\nFailed to install {version} (exit code {e.returncode}).")
        print("\nTry running the command manually:")
        print(f"PYTHON --py-install {version}")
        sys.exit(1)

if __name__ == "__main__":
    main()
