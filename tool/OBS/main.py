#!/usr/bin/env python3
"""OBS Tool — CLI harness for OBS Studio - Create and manage streaming/recording scenes via command line

Wraps the CLI-Anything obs-studio harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/obs-studio
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


class OBSTool(ToolBase):
    def __init__(self):
        super().__init__("OBS")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = OBSTool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}OBS{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for OBS Studio - Create and manage streaming/recording scenes via command line{RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}project{RESET}")
        print(f"    {DIM}new         {RESET}")
        print(f"    {DIM}open        {RESET}")
        print(f"    {DIM}save        {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}json        {RESET}")
        print(f"  {BOLD}session{RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}undo        {RESET}")
        print(f"    {DIM}redo        {RESET}")
        print(f"    {DIM}history     {RESET}")
        print(f"  {BOLD}scene_group{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}duplicate   {RESET}")
        print(f"    {DIM}set-active  {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}source_group{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}duplicate   {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}transform   {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}filter_group{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}set         {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}list-available{RESET}")
        print(f"  {BOLD}audio_group{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}volume      {RESET}")
        print(f"    {DIM}mute        {RESET}")
        print(f"    {DIM}unmute      {RESET}")
        print(f"    {DIM}... +2 more{RESET}")
        print(f"  {BOLD}transition_group{RESET}")
        print(f"    {DIM}add         {RESET}")
        print(f"    {DIM}remove      {RESET}")
        print(f"    {DIM}set-active  {RESET}")
        print(f"    {DIM}duration    {RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"  {BOLD}output_group{RESET}")
        print(f"    {DIM}streaming   {RESET}")
        print(f"    {DIM}recording   {RESET}")
        print(f"    {DIM}settings    {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"    {DIM}presets     {RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything obs-studio")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.obs_studio.obs_studio_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
