#!/usr/bin/env python3
"""INKSCAPE Tool — CLI harness for Inkscape - SVG vector graphics with export via inkscape --export-filename. Requires: inkscape (apt install inkscape)

Wraps the CLI-Anything inkscape harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/inkscape
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


class INKSCAPETool(ToolBase):
    def __init__(self):
        super().__init__("INKSCAPE")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = INKSCAPETool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}INKSCAPE{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for Inkscape - SVG vector graphics with export via inkscape --export-filename. Requires: inkscape (apt install inkscape){RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}document{RESET}")
        print(f"    {DIM}new         {RESET}")
        print(f"    {DIM}open        {RESET}")
        print(f"    {DIM}save        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}profiles    {RESET}")
        print(f"    {DIM}... +3 more{RESET}")
        print(f"  {BOLD}gradient{RESET}")
        print(f"    {DIM}add-linear  {RESET}")
        print(f"    {DIM}add-radial  {RESET}")
        print(f"    {DIM}apply       {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}layer{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}move-object {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}... +2 more{RESET}")
        print(f"  {BOLD}session{RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}undo        {RESET}")
        print(f"    {DIM}redo        {RESET}")
        print(f"    {DIM}history     {RESET}")
        print(f"  {BOLD}shape{RESET}")
        print(f"    {DIM}add-rect    {RESET}")
        print(f"    {DIM}add-circle  {RESET}")
        print(f"    {DIM}add-ellipse {RESET}")
        print(f"    {DIM}add-line    {RESET}")
        print(f"    {DIM}add-polygon {RESET}")
        print(f"    {DIM}... +6 more{RESET}")
        print(f"  {BOLD}style{RESET}")
        print(f"    {DIM}set-fill    {RESET}")
        print(f"    {DIM}set-stroke  {RESET}")
        print(f"    {DIM}set-opacity {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}get         {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}text{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}transform{RESET}")
        print(f"    {DIM}translate   {RESET}")
        print(f"    {DIM}rotate      {RESET}")
        print(f"    {DIM}scale       {RESET}")
        print(f"    {DIM}skew-x      {RESET}")
        print(f"    {DIM}skew-y      {RESET}")
        print(f"    {DIM}... +2 more{RESET}")
        print(f"  {DIM}... +2 more groups{RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything inkscape")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.inkscape.inkscape_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
