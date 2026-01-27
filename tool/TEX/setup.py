#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for TEX tool.
Installs required Python dependencies and optionally TinyTeX.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.config import get_color
    from logic.utils import get_logic_dir
except ImportError:
    # Fallback if logic not available
    class ProgressTuringMachine:
        def add_stage(self, stage): stage.action()
        def run(self, **kwargs): return True
    class TuringStage:
        def __init__(self, **kwargs): self.action = kwargs.get('action')
    def get_color(n, d=""): return d
    def get_logic_dir(d): return d / "logic"

def run_command(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\nError: {res.stderr}")
    return res.stdout

def install_deps():
    """Install python dependencies."""
    cmd = [sys.executable, "-m", "pip", "install", "tinytex"]
    run_command(cmd)
    return True

def install_tinytex():
    """Install TinyTeX distribution locally."""
    install_dir = project_root / "tool" / "TEX" / "data" / "install"
    tinytex_root = install_dir / "TinyTeX"
    
    if tinytex_root.exists():
        return True # Already installed
        
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the tinytex python module to install
    import tinytex
    tinytex.install_tinytex(force=True, dir=str(tinytex_root))
    return True

def main():
    tm = ProgressTuringMachine()
    
    tm.add_stage(TuringStage(
        name="Python dependencies",
        action=install_deps,
        active_status="Installing",
        success_status="Installed",
        fail_status="Failed to install"
    ))
    
    # Optional: TinyTeX installation can be large, maybe ask user?
    # For now, let's make it part of setup.
    tm.add_stage(TuringStage(
        name="TinyTeX distribution",
        action=install_tinytex,
        active_status="Installing (this may take a few minutes)",
        success_status="Installed",
        fail_status="Failed to install"
    ))
    
    if tm.run(ephemeral=True):
        print("\nTEX tool setup complete!")
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())

