#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Setup script for TEX tool.
Installs TinyTeX distribution locally.
Python dependencies (tinytex) are handled by ToolEngine via tool.json.
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
except ImportError:
    class ProgressTuringMachine:
        def add_stage(self, stage): stage.action()
        def run(self, **kwargs): return True
    class TuringStage:
        def __init__(self, **kwargs): self.action = kwargs.get('action')

def install_tinytex():
    """Install TinyTeX distribution locally."""
    install_dir = project_root / "tool" / "TEX" / "data" / "install"
    tinytex_root = install_dir / "TinyTeX"
    
    if tinytex_root.exists():
        return True # Already installed
        
    install_dir.mkdir(parents=True, exist_ok=True)
    
    # Use the tinytex python module to install, but capture its output
    try:
        import tinytex
        from contextlib import redirect_stdout, redirect_stderr
        
        with open(os.devnull, 'w') as devnull:
            with redirect_stdout(devnull), redirect_stderr(devnull):
                tinytex.install_tinytex(force=True, dir=str(tinytex_root))
        return True
    except:
        return False

def main():
    tm = ProgressTuringMachine()
    
    tm.add_stage(TuringStage(
        name="TinyTeX distribution",
        action=install_tinytex,
        active_status="Installing (this may take a few minutes)",
        success_status="Installed",
        fail_status="Failed to install"
    ))
    
    if tm.run(ephemeral=True):
        return 0
    return 1

if __name__ == "__main__":
    sys.exit(main())
