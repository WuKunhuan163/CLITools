#!/usr/bin/env python3
"""DRAWIO Tool — CLI harness for Draw.io - Diagram creation and export via draw.io CLI. Requires: draw.io desktop app (draw.io --export)

Wraps the CLI-Anything drawio harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/drawio
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


class DRAWIOTool(ToolBase):
    def __init__(self):
        super().__init__("DRAWIO")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = DRAWIOTool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}DRAWIO{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for Draw.io - Diagram creation and export via draw.io CLI. Requires: draw.io desktop app (draw.io --export){RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}connect{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}label       {RESET}")
        print(f"    {DIM}style       {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}export{RESET}")
        print(f"    {DIM}render      {RESET}")
        print(f"    {DIM}formats     {RESET}")
        print(f"  {BOLD}page{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}rename      {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}project{RESET}")
        print(f"    {DIM}new         {RESET}")
        print(f"    {DIM}open        {RESET}")
        print(f"    {DIM}save        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}xml         {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}session{RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}undo        {RESET}")
        print(f"    {DIM}redo        {RESET}")
        print(f"    {DIM}save-state  {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}shape{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}label       {RESET}")
        print(f"    {DIM}move        {RESET}")
        print(f"    {DIM}... +4 more{RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything drawio")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.drawio.drawio_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
