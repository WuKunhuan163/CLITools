#!/usr/bin/env python3
"""ZOOM Tool — CLI harness for Zoom - Meeting management via Zoom REST API (OAuth2). Requires: Zoom account + OAuth app credentials

Wraps the CLI-Anything zoom harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/zoom
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


class ZOOMTool(ToolBase):
    def __init__(self):
        super().__init__("ZOOM")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = ZOOMTool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}ZOOM{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for Zoom - Meeting management via Zoom REST API (OAuth2). Requires: Zoom account + OAuth app credentials{RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}auth{RESET}")
        print(f"    {DIM}setup       {RESET}")
        print(f"    {DIM}login       {RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}logout      {RESET}")
        print(f"  {BOLD}meeting{RESET}")
        print(f"    {DIM}create      {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}update      {RESET}")
        print(f"    {DIM}delete      {RESET}")
        print(f"    {DIM}... +2 more{RESET}")
        print(f"  {BOLD}participant{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}add-batch   {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}attended    {RESET}")
        print(f"  {BOLD}recording{RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}files       {RESET}")
        print(f"    {DIM}download    {RESET}")
        print(f"    {DIM}delete      {RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything zoom")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.zoom.zoom_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
