#!/usr/bin/env python3

# Fix shadowing: Remove script directory from sys.path[0] if present
import sys
from pathlib import Path
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]
import sys
import argparse


def _git_bin():
    try:
        from tool.GIT.interface.main import get_system_git
        return get_system_git()
    except ImportError:
        return _git_bin()
import json
import subprocess
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color
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
    parser.add_argument("--install", help="Install a font file (path or remote name) or migrate from tmp")
    parser.add_argument("--name", help="Custom name for the font (when installing from path)")
    
    # Analyze
    parser_analyze = subparsers.add_parser("analyze", help="Generate character table and heuristics for a font")
    parser_analyze.add_argument("name", type=str, help="Font name or path")
    
    # Get
    parser_get = subparsers.add_parser("get", help="Get heuristics for a font")
    parser_get.add_argument("name", type=str, help="Font name")
    
    # List
    subparsers.add_parser("list", help="List installed fonts")
    
    # Download (Legacy, now part of --install)
    parser_download = subparsers.add_parser("download", help="Download font family from Google Fonts")
    parser_download.add_argument("family", type=str, help="Font family name (e.g. 'Open Sans')")

    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()
    
    RED = get_color("RED")
    BOLD = get_color("BOLD")
    BLUE = get_color("BLUE")
    GREEN = get_color("GREEN")
    RESET = get_color("RESET")

    if args.install:
        target = args.install
        if Path(target).exists():
            # Local file installation
            font_path = Path(target)
            name = args.name or font_path.stem
            # deploy_font_file already handles blue bold and erasable lines
            if tool.manager.deploy_font_file(font_path, name):
                print(f"\r\033[K{GREEN}Successfully installed{RESET} {name}.")
            else:
                print(f"\r\033[K{RED}Error{RESET}: Failed to install {name}.")
        elif target == "tmp":
            # Migration from tmp
            print(f"{BLUE}Migrating{RESET} fonts from tmp/fontsgeek...", end="", flush=True)
            tool.manager.migrate_from_tmp()
            print(f"\r\033[K{GREEN}Successfully migrated{RESET} fonts.")
        else:
            # Remote download from tool:resource
            family = target
            norm_name = tool.manager.normalize_name(family)
            print(f"{BLUE}Fetching{RESET} font '{family}' from remote resource...", end="", flush=True)
            
            # Use git checkout to get the font from origin/tool
            rel_path = f"resource/tool/FONT/data/install/{norm_name}"
            try:
                subprocess.run([_git_bin(), "fetch", "origin", "tool"], capture_output=True, check=True)
                res = subprocess.run([_git_bin(), "checkout", "origin/tool", "--", rel_path], capture_output=True, text=True)
                if res.returncode == 0:
                    print(f"\r\033[K{GREEN}Successfully installed{RESET} {family}.")
                else:
                    print(f"\r\033[K{RED}Error{RESET}: Font '{family}' not found in remote resource.")
            except Exception as e:
                print(f"\r\033[K{RED}Error{RESET}: Failed to fetch font: {e}")
            
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
        
        print(f"{BLUE}Analyzing{RESET} font {font_name}...", end="", flush=True)
        from tool.FONT.logic.bbox_analyzer import BBoxAnalyzer
        analyzer = BBoxAnalyzer(font_path, output_dir, font_name)
        pdf = analyzer.generate_source_pdf()
        analyzer.analyze(pdf)
        print(f"\r\033[K{GREEN}Analysis complete{RESET}: {output_dir}")

    elif args.subcommand == "get":
        norm_name = tool.manager.normalize_name(args.name)
        info_path = tool.manager.resource_dir / norm_name / "info.json"
        if info_path.exists():
            with open(info_path, 'r') as f:
                print(json.dumps(json.load(f), indent=2, ensure_ascii=False))
        else:
            print(f"\r\033[K{RED}Error{RESET}: Heuristics for '{args.name}' not found.")
                
    elif args.subcommand == "list":
        print(f"{BOLD}Installed Fonts:{RESET}")
        if tool.manager.resource_dir.exists():
            for item in tool.manager.resource_dir.iterdir():
                if item.is_dir():
                    print(f"- {item.name}")
                    
    elif args.subcommand == "download":
        family = args.family
        print(f"{BLUE}Downloading{RESET} font family '{family}' from Google Fonts...", end="", flush=True)
        success, reason = tool.manager.download_and_deploy_google_font(family)
        if success:
            print(f"\r\033[K{GREEN}Successfully deployed{RESET} {family}. {BOLD}Reason{RESET}: {reason}")
        else:
            print(f"\r\033[K{RED}Error{RESET}: Failed to download {family}. {BOLD}Reason{RESET}: {reason}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
