#!/usr/bin/env python3
"""TOOL — AITerminalTools root CLI manager.

Minimal entry point: inherits ToolBase, delegates to stateless argparse router.
The base discovers commands by traversing logic/_/ (eco) and logic/ (hierarchical).
"""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from interface.tool import ToolBase

tool = ToolBase("TOOL", is_root=True)
if tool.handle_command_line():
    sys.exit(0)
