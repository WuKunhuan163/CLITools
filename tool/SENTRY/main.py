#!/usr/bin/env python3
"""SENTRY tool — entry point.

Minimal main.py: inherits ToolBase, delegates to stateless argparse router.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from interface.tool import ToolBase

tool = ToolBase("SENTRY")
if tool.handle_command_line():
    sys.exit(0)
