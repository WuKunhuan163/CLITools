#!/usr/bin/env python3
"""GOOGLE.GS - Google Scholar tool (ToS-restricted).

Google Scholar's Terms of Service explicitly prohibit automated access,
scraping, and bot-driven interaction. This tool's CDMCP implementation
was removed to comply with those terms.

See for_agent.md for alternatives (SerpAPI, Semantic Scholar API, etc.).
"""
import sys
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.config import get_color


def main():
    BOLD = get_color("BOLD")
    DIM = get_color("DIM")
    YELLOW = get_color("YELLOW")
    RED = get_color("RED")
    RESET = get_color("RESET")

    print(f"\n  {BOLD}{RED}GOOGLE.GS — Restricted{RESET}")
    print(f"  {DIM}Google Scholar's Terms of Service prohibit automated access.{RESET}")
    print(f"  {DIM}The CDMCP browser automation for this tool has been removed.{RESET}")
    print()
    print(f"  {BOLD}Alternatives:{RESET}")
    print(f"  {DIM}  - SerpAPI (https://serpapi.com/google-scholar-api) — paid, structured JSON{RESET}")
    print(f"  {DIM}  - Semantic Scholar API (https://api.semanticscholar.org/) — free, academic{RESET}")
    print(f"  {DIM}  - OpenAlex API (https://openalex.org/) — free, open{RESET}")
    print(f"  {DIM}  - Google Search Researcher API — restricted to approved academics{RESET}")
    print()
    print(f"  {YELLOW}To integrate an alternative, implement a provider in logic/providers/.{RESET}")
    print()


if __name__ == "__main__":
    main()
