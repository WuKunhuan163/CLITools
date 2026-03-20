#!/usr/bin/env python3
"""AUDACITY Tool — CLI harness for Audacity - Audio editing and processing via sox. Requires: sox (apt install sox)

Wraps the CLI-Anything audacity harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/audacity
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


class AUDACITYTool(ToolBase):
    def __init__(self):
        super().__init__("AUDACITY")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = AUDACITYTool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}AUDACITY{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for Audacity - Audio editing and processing via sox. Requires: sox (apt install sox){RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}clip{RESET}")
        print(f"    {DIM}import      {RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}trim        {RESET}")
        print(f"    {DIM}split       {RESET}")
        print(f"    {DIM}... +2 more{RESET}")
        print(f"  {BOLD}label{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}media{RESET}")
        print(f"    {DIM}probe       {RESET}")
        print(f"    {DIM}check       {RESET}")
        print(f"  {BOLD}project{RESET}")
        print(f"    {DIM}new         {RESET}")
        print(f"    {DIM}open        {RESET}")
        print(f"    {DIM}save        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}settings    {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}selection{RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}all         {RESET}")
        print(f"    {DIM}none        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"  {BOLD}track{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"  {BOLD}effect_group{RESET}")
        print(f"    {DIM}list-available{RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}export_group{RESET}")
        print(f"    {DIM}presets     {RESET}")
        print(f"    {DIM}preset-info {RESET}")
        print(f"    {DIM}render      {RESET}")
        print(f"  {DIM}... +1 more groups{RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything audacity")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.audacity.audacity_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
