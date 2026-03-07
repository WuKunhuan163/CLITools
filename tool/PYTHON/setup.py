#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
from pathlib import Path

# Add project root to sys.path
def find_project_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_project_root()
if project_root:
    sys.path.insert(0, str(project_root))

import subprocess
from interface.tool import ToolEngine

def setup():
    tool_name = "PYTHON"
    engine = ToolEngine(tool_name, project_root)
    if not engine.install():
        return False
        
    # After basic engine install (shortcut etc.), ensure a default version is installed
    # Use the python tool itself to perform the installation
    python_bin = project_root / "bin" / "PYTHON" / "PYTHON"
    if not python_bin.exists():
        python_bin = project_root / "bin" / "PYTHON"
    if python_bin.exists():
        import json
        config_path = script_dir / "tool.json"
        default_version = "3.11.14"
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    default_version = json.load(f).get("default_version", "3.11.14")
            except: pass
            
        # Check if already installed
        res = subprocess.run([str(python_bin), "--py-list"], capture_output=True, text=True)
        if "(installed)" not in res.stdout:
            # Only print if we are actually going to install something
            print(f"\nInstalling default Python version: {default_version}...")
            subprocess.run([str(python_bin), "--py-install", default_version])
            
        # Automatically enable managed python (creates symlinks in bin/)
        subprocess.run([str(python_bin), "--enable"])
            
    return True

if __name__ == "__main__":
    setup()
