#!/usr/bin/env python3
import sys
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

def main():
    print("--- Running setup for SEARCH ---")
    print("Setup complete.")

if __name__ == "__main__":
    main()

