#!/usr/bin/env python3
import sys
from pathlib import Path

# Universal path resolver bootstrap
_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolEngine

def setup():
    tool_name = "SHOWDOC"
    engine = ToolEngine(tool_name, project_root)
    
    # 1. Standard installation (dependencies + shortcut)
    return engine.install()

if __name__ == "__main__":
    setup()
