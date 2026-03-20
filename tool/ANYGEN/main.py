#!/usr/bin/env python3
"""ANYGEN Tool — CLI harness for AnyGen OpenAPI - Generate docs, slides, websites and more via AnyGen cloud API. Requires: ANYGEN_API_KEY

Wraps the CLI-Anything anygen harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/anygen
"""
import sys
import os
from pathlib import Path

script_path = Path(__file__).resolve()
project_root = script_path.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from interface.tool import ToolBase
from interface.config import get_color

BOLD = get_color("BOLD")
DIM = get_color("DIM")
RESET = get_color("RESET")
GREEN = get_color("GREEN")
RED = get_color("RED")


class ANYGENTool(ToolBase):
    def __init__(self):
        super().__init__("ANYGEN")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = ANYGENTool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}ANYGEN{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for AnyGen OpenAPI - Generate docs, slides, websites and more via AnyGen cloud API. Requires: ANYGEN_API_KEY{RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}config{RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}get         {RESET}")
        print(f"    {DIM}delete      {RESET}")
        print(f"    {DIM}path        {RESET}")
        print(f"  {BOLD}file{RESET}")
        print(f"    {DIM}upload      {RESET}")
        print(f"  {BOLD}session{RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}history     {RESET}")
        print(f"    {DIM}undo        {RESET}")
        print(f"    {DIM}redo        {RESET}")
        print(f"  {BOLD}task{RESET}")
        print(f"    {DIM}create      {RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}poll        {RESET}")
        print(f"    {DIM}download    {RESET}")
        print(f"    {DIM}thumbnail   {RESET}")
        print(f"    {DIM}... +3 more{RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything anygen")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.anygen.anygen_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
