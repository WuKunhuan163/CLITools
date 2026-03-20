#!/usr/bin/env python3
"""TOOL — AITerminalTools root CLI manager.

Minimal entry point: inherits ToolBase, delegates to stateless argparse router.
The base discovers commands by traversing logic/_/ (eco) and logic/ (hierarchical).

Static path resolution: this file is at the project root (or symlinked from bin/).
It uses __file__ to locate __/interface/base.py deterministically.
"""
import sys
from pathlib import Path

_this = Path(__file__).resolve()
_root = _this.parent
if _root.name == "bin":
    _root = _root.parent
sys.path.insert(0, str(_root))

from interface.base import ToolBase

tool = ToolBase("TOOL", is_root=True)
if tool.handle_command_line():
    sys.exit(0)
