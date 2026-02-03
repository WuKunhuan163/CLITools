#!/usr/bin/env python3
import sys
import argparse
import json
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color
from tool.FONT.logic.engine import FontEngine

def main():
    tool = ToolBase("FONT")
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="Tool FONT: Font management and analysis")
    subparsers = parser.add_subparsers(dest="subcommand", help="Available subcommands")
    
    # Analyze
    parser_analyze = subparsers.add_parser("analyze", help="Analyze a font file for heuristics")
    parser_analyze.add_argument("path", type=str, help="Path to the font file")
    
    # Install
    parser_install = subparsers.add_parser("install", help="Install a font from URL")
    parser_install.add_argument("name", type=str, help="Name for the font")
    parser_install.add_argument("url", type=str, help="URL to the font file")
    
    # Get
    parser_get = subparsers.add_parser("get", help="Get heuristics for a font")
    parser_get.add_argument("name", type=str, help="Font name")
    
    # Search
    parser_search = subparsers.add_parser("search", help="Search for fonts on GitHub")
    parser_search.add_argument("repo", type=str, help="GitHub repo (e.g. ryanoasis/nerd-fonts)")
    
    args, unknown = parser.parse_known_args()
    
    engine = FontEngine(script_dir / "data")
    
    if args.subcommand == "analyze":
        BOLD = get_color("BOLD")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        print(f"{BOLD}{BLUE}Analyzing{RESET} font {args.path}...")
        metrics = engine.analyze_font(args.path)
        if metrics:
            print(json.dumps(metrics, indent=2))
        else:
            print("Failed to analyze font.")
            
    elif args.subcommand == "install":
        BOLD = get_color("BOLD")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        print(f"{BOLD}{BLUE}Installing{RESET} font {args.name} from {args.url}...")
        metrics = engine.install_font_from_url(args.name, args.url)
        if metrics:
            print(f"Successfully installed and analyzed {args.name}")
        else:
            print(f"Failed to install {args.name}")

    elif args.subcommand == "get":
        name = args.name
        if name in engine.heuristics:
            print(json.dumps(engine.heuristics[name], indent=2))
        else:
            # Try path if name exists as file
            if Path(name).exists():
                metrics = engine.analyze_font(name)
                print(json.dumps(metrics, indent=2))
            else:
                print(f"Font '{name}' not found.")
                
    elif args.subcommand == "search":
        BOLD = get_color("BOLD")
        BLUE = get_color("BLUE")
        RESET = get_color("RESET")
        print(f"{BOLD}{BLUE}Searching{RESET} repository {args.repo}...")
        assets = engine.search_github_fonts(args.repo)
        if assets:
            for asset in assets:
                print(f"- {asset['name']}: {asset['url']}")
        else:
            print("No fonts found in the latest release.")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
