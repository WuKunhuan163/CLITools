#!/usr/bin/env python3
import os
import shutil
from pathlib import Path

def main():
    script_dir = Path(__file__).resolve().parent
    install_dir = script_dir / "proj" / "install"
    
    if install_dir.exists():
        print(f"Cleaning up Python installations in {install_dir}...")
        shutil.rmtree(install_dir)
        print("Installations cleared.")
    
    # Ensure the directory exists but is empty
    install_dir.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()

