#!/usr/bin/env python3
"""GITLAB tool — entry point.

Minimal main.py: inherits ToolBase, delegates to stateless argparse router.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from interface.tool import ToolBase

tool = ToolBase("GITLAB")
if tool.handle_command_line():
    sys.exit(0)
