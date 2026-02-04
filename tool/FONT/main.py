#!/usr/bin/env python3
import sys
import argparse
import json
import os
import subprocess
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color
from tool.FONT.logic.engine import FontManager
from tool.FONT.logic.bbox_analyzer import BBoxAnalyzer

class FontTool(ToolBase):
    def __init__(self):
        super().__init__("FONT")
        self.manager = FontManager(self.project_root)

def main():
    tool = FontTool()
    parser = argparse.ArgumentParser(description="Tool FONT: Font management and analysis")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")
    
    # Install (alias for migrating from tmp or manual)
    parser_install = subparsers.add_parser("install", help="Install fonts from tmp/fontsgeek")
    
    # Analyze
    parser_analyze = subparsers.add_parser("analyze", help="Generate character table and heuristics for a font")
    parser_analyze.add_argument("name", type=str, help="Font name or path")
    
    # Get
    parser_get = subparsers.add_parser("get", help="Get heuristics for a font")
    parser_get.add_argument("name", type=str, help="Font name")
    
    # List
    parser_list = subparsers.add_parser("list", help="List installed fonts")

    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()
    
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")

    if args.subcommand == "install":
        print(f"{BOLD}{BLUE}Migrating{RESET} fonts from tmp/fontsgeek...")
        tool.manager.migrate_from_tmp()
        print(f"{BOLD}{GREEN}Done!{RESET}")
            
    elif args.subcommand == "analyze":
        font_name = args.name
        font_path = tool.manager.get_font_path(font_name)
        if not font_path:
            if Path(font_name).exists():
                font_path = font_name
                font_name = Path(font_name).stem
            else:
                print(f"Font '{font_name}' not found.")
                return 1
        
        norm_name = tool.manager.normalize_name(font_name)
        output_dir = tool.manager.resource_dir / norm_name / "bbox_analysis"
        
        print(f"{BOLD}{BLUE}Analyzing{RESET} font {font_name}...")
        analyzer = BBoxAnalyzer(font_path, output_dir, font_name)
        pdf = analyzer.generate_source_pdf()
        analyzer.analyze(pdf)
        print(f"{BOLD}{GREEN}Analysis complete{RESET}: {output_dir}")

    elif args.subcommand == "get":
        norm_name = tool.manager.normalize_name(args.name)
        info_path = tool.manager.resource_dir / norm_name / "info.json"
        if info_path.exists():
            with open(info_path, 'r') as f:
                print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        else:
            print(f"Heuristics for '{args.name}' not found.")
                
    elif args.subcommand == "list":
        print(f"{BOLD}Installed Fonts:{RESET}")
        if tool.manager.resource_dir.exists():
            for item in tool.manager.resource_dir.iterdir():
                if item.is_dir():
                    print(f"- {item.name}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
