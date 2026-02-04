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
class FontTool(ToolBase):
    def __init__(self):
        super().__init__("FONT")
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            from tool.FONT.logic.engine import FontManager
            self._manager = FontManager(self.project_root)
        return self._manager

def main():
    tool = FontTool()
    parser = argparse.ArgumentParser(description="Tool FONT: Font management and analysis")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")
    
    # Install
    parser_install = subparsers.add_parser("install", help="Install a font file or migrate from tmp")
    parser_install.add_argument("path", nargs="?", help="Path to the font file to install")
    parser_install.add_argument("--name", help="Custom name for the font")
    
    # Analyze
    parser_analyze = subparsers.add_parser("analyze", help="Generate character table and heuristics for a font")
    parser_analyze.add_argument("name", type=str, help="Font name or path")
    
    # Get
    parser_get = subparsers.add_parser("get", help="Get heuristics for a font")
    parser_get.add_argument("name", type=str, help="Font name")
    
    # List
    parser_list = subparsers.add_parser("list", help="List installed fonts")
    
    # Download
    parser_download = subparsers.add_parser("download", help="Download font family from Google Fonts")
    parser_download.add_argument("family", type=str, help="Font family name (e.g. 'Open Sans')")

    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()
    
    RED = get_color("RED", "\033[31m")
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")

    if args.subcommand == "install":
        if args.path:
            font_path = Path(args.path)
            if not font_path.exists():
                print(f"\r\033[K{BOLD}{RED}Error{RESET}: File not found: {args.path}")
                return 1
            name = args.name or font_path.stem
            print(f"{BOLD}{BLUE}Installing{RESET} font {name}...", end="", flush=True)
            tool.manager.deploy_font_file(font_path, name)
            print(f"\r\033[K{BOLD}{GREEN}Successfully installed{RESET} {name}.")
        else:
            print(f"{BOLD}{BLUE}Migrating{RESET} fonts from tmp/fontsgeek...", end="", flush=True)
            tool.manager.migrate_from_tmp()
            print(f"\r\033[K{BOLD}{GREEN}Successfully migrated{RESET} fonts.")
            
    elif args.subcommand == "analyze":
        font_name = args.name
        font_path = tool.manager.get_font_path(font_name)
        if not font_path:
            if Path(font_name).exists():
                font_path = font_name
                font_name = Path(font_name).stem
            else:
                print(f"\r\033[K{BOLD}{RED}Error{RESET}: Font '{font_name}' not found.")
                return 1
        
        norm_name = tool.manager.normalize_name(font_name)
        output_dir = tool.manager.resource_dir / norm_name / "bbox_analysis"
        
        print(f"{BOLD}{BLUE}Analyzing{RESET} font {font_name}...", end="", flush=True)
        from tool.FONT.logic.bbox_analyzer import BBoxAnalyzer
        analyzer = BBoxAnalyzer(font_path, output_dir, font_name)
        pdf = analyzer.generate_source_pdf()
        analyzer.analyze(pdf)
        print(f"\r\033[K{BOLD}{GREEN}Analysis complete{RESET}: {output_dir}")

    elif args.subcommand == "get":
        norm_name = tool.manager.normalize_name(args.name)
        info_path = tool.manager.resource_dir / norm_name / "info.json"
        if info_path.exists():
            with open(info_path, 'r') as f:
                print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        else:
            print(f"\r\033[K{BOLD}{RED}Error{RESET}: Heuristics for '{args.name}' not found.")
                
    elif args.subcommand == "list":
        print(f"{BOLD}Installed Fonts:{RESET}")
        if tool.manager.resource_dir.exists():
            for item in tool.manager.resource_dir.iterdir():
                if item.is_dir():
                    print(f"- {item.name}")
                    
    elif args.subcommand == "download":
        family = args.family
        print(f"{BOLD}{BLUE}Downloading{RESET} font family '{family}' from Google Fonts...", end="", flush=True)
        success, reason = tool.manager.download_and_deploy_google_font(family)
        if success:
            print(f"\r\033[K{BOLD}{GREEN}Successfully deployed{RESET} {family}. {BOLD}Reason{RESET}: {reason}")
        else:
            print(f"\r\033[K{BOLD}{RED}Error{RESET}: Failed to download {family}. {BOLD}Reason{RESET}: {reason}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
