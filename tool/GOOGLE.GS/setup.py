#!/usr/bin/env python3
"""Setup for GOOGLE.GS (Google Scholar MCP)."""

import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)


def main():
    from interface.tool import ToolBase
    ToolBase("GOOGLE.GS")
    print("GOOGLE.GS setup complete. Requires GOOGLE.CDMCP and Chrome with CDP.")


if __name__ == "__main__":
    main()
