#!/usr/bin/env python3
"""FITZ — PDF manipulation via PyMuPDF.

Minimal entry point: inherits ToolBase, delegates to stateless argparse router.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from interface.tool import ToolBase

tool = ToolBase("FITZ")
if tool.handle_command_line():
    sys.exit(0)

import fitz
fitz.TOOLS.mupdf_display_errors(False)
print("FITZ tool active.")
