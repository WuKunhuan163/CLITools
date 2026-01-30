#!/usr/bin/env python3
import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

def main():
    print("--- Running setup for READ ---")
    print("Setup complete.")

if __name__ == "__main__":
    main()
