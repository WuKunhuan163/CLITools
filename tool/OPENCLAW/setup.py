#!/usr/bin/env python3
import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.setup.engine import ToolEngine

def setup():
    tool_name = "OPENCLAW"
    engine = ToolEngine(tool_name, _r)
    return engine.install()

if __name__ == "__main__":
    setup()
