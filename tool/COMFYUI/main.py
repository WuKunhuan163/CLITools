#!/usr/bin/env python3
"""COMFYUI Tool — CLI harness for ComfyUI - AI image generation workflow management via ComfyUI REST API. Requires: ComfyUI running at http://localhost:8188

Wraps the CLI-Anything comfyui harness.
Upstream: https://github.com/HKUDS/CLI-Anything/tree/main/comfyui
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


class COMFYUITool(ToolBase):
    def __init__(self):
        super().__init__("COMFYUI")


def _get_upstream_package():
    return Path(__file__).resolve().parent / "data" / "upstream" / "CLI-Anything" / "agent-harness"


def main():
    tool = COMFYUITool()

    if len(sys.argv) < 2 or sys.argv[1] in ["-h", "--help", "help"]:
        print(f"\n  {BOLD}COMFYUI{RESET} (via CLI-Anything)")
        print(f"  {DIM}CLI harness for ComfyUI - AI image generation workflow management via ComfyUI REST API. Requires: ComfyUI running at http://localhost:8188{RESET}")
        print()
        print(f"  {BOLD}Commands{RESET}")
        print(f"  {BOLD}images{RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}download    {RESET}")
        print(f"    {DIM}download-all{RESET}")
        print(f"  {BOLD}models{RESET}")
        print(f"    {DIM}checkpoints {RESET}")
        print(f"    {DIM}loras       {RESET}")
        print(f"    {DIM}vaes        {RESET}")
        print(f"    {DIM}controlnets {RESET}")
        print(f"    {DIM}node-info   {RESET}")
        print(f"    {DIM}... +1 more{RESET}")
        print(f"  {BOLD}queue{RESET}")
        print(f"    {DIM}prompt      {RESET}")
        print(f"    {DIM}status      {RESET}")
        print(f"    {DIM}clear       {RESET}")
        print(f"    {DIM}history     {RESET}")
        print(f"    {DIM}interrupt   {RESET}")
        print(f"  {BOLD}system{RESET}")
        print(f"    {DIM}stats       {RESET}")
        print(f"    {DIM}info        {RESET}")
        print(f"  {BOLD}workflow{RESET}")
        print(f"    {DIM}list        {RESET}")
        print(f"    {DIM}load        {RESET}")
        print(f"    {DIM}validate    {RESET}")
        print()
        print(f"  {BOLD}Upstream{RESET}")
        print(f"  {DIM}Package: {_get_upstream_package()}{RESET}")
        print(f"  {DIM}Install: pip install -e {_get_upstream_package()}{RESET}")
        print()
        return 0

    upstream = _get_upstream_package()
    if not upstream.exists():
        print(f"  {BOLD}{RED}Not installed.{RESET} Run: TOOL --migrate --draft-tool CLI-Anything comfyui")
        return 1

    pkg_path = str(upstream)
    if pkg_path not in sys.path:
        sys.path.insert(0, pkg_path)

    try:
        from cli_anything.comfyui.comfyui_cli import main as cli_main
        cli_main()
    except ImportError as e:
        print(f"  {BOLD}{RED}Import error.{RESET} {e}")
        print(f"  Try: pip install -e {upstream}")
        return 1
    except SystemExit as e:
        return e.code or 0


if __name__ == "__main__":
    sys.exit(main() or 0)
