#!/usr/bin/env python3
"""GOOGLE.GS - Google Scholar automation via CDMCP."""
import sys
import argparse
import json
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.mcp import MCPToolBase
from interface.config import get_color


def _load_api():
    import importlib.util
    api_path = Path(__file__).resolve().parent / "logic" / "chrome" / "api.py"
    spec = importlib.util.spec_from_file_location("gs_api", str(api_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    tool = MCPToolBase("GOOGLE.GS", session_name="scholar")

    parser = argparse.ArgumentParser(
        description="Google Scholar automation via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("boot", help="Boot Scholar session in dedicated window")
    sub.add_parser("state", help="Get comprehensive MCP state")

    p_search = sub.add_parser("search", help="Search for papers")
    p_search.add_argument("query", nargs="+", help="Search query")
    p_search.add_argument("--year-from", type=int, default=0, help="Start year filter")
    p_search.add_argument("--year-to", type=int, default=0, help="End year filter")

    sub.add_parser("results", help="Get current search results")
    sub.add_parser("next", help="Go to next page of results")
    sub.add_parser("prev", help="Go to previous page of results")

    p_open = sub.add_parser("open", help="Open a paper by index")
    p_open.add_argument("--index", type=int, default=0, help="Result index (0-based)")

    p_save = sub.add_parser("save", help="Save a paper to library")
    p_save.add_argument("--index", type=int, default=0, help="Result index")

    p_cite = sub.add_parser("cite", help="Get citation for a paper")
    p_cite.add_argument("--index", type=int, default=0, help="Result index")

    p_cited = sub.add_parser("cited-by", help="Find papers citing this paper")
    p_cited.add_argument("--index", type=int, default=0, help="Result index")

    p_pdf = sub.add_parser("pdf", help="Get PDF URL for a paper")
    p_pdf.add_argument("--index", type=int, default=0, help="Result index")

    p_filter = sub.add_parser("filter", help="Apply search filters")
    p_filter.add_argument("--time", dest="time_filter", default=None,
                          help="Time filter: any, 2026, 2025, 2022, or year")
    p_filter.add_argument("--sort", default=None, choices=["relevance", "date"])

    sub.add_parser("profile", help="Open your Google Scholar profile")
    sub.add_parser("library", help="Open your saved papers library")

    p_author = sub.add_parser("author", help="Search for an author")
    p_author.add_argument("name", nargs="+", help="Author name")

    p_shot = sub.add_parser("screenshot", help="Take screenshot of Scholar tab")
    p_shot.add_argument("--output", default="", help="Output path")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    BLUE = get_color("BLUE")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    api = _load_api()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "boot":
        r = api.boot_session()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Booted{RESET} Scholar session [{r.get('session_id','?')[:8]}].")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "state":
        print(json.dumps(api.get_mcp_state(), indent=2))

    elif args.command == "search":
        query = " ".join(args.query)
        print(f"  {BLUE}Searching:{RESET} {query}")
        r = api.search(query, year_from=args.year_from, year_to=args.year_to)
        if r.get("ok"):
            print(f"  {GREEN}Found {r['count']} results{RESET}")
            for p in r.get("results", []):
                print(f"  [{p.get('index','?')}] {p.get('title','')[:70]}")
                print(f"      {p.get('authors','')[:70]}")
                if p.get("cited"):
                    print(f"      {p['cited']}")
                print()
        else:
            print(f"  {RED}Error:{RESET} {r.get('error', '?')}")

    elif args.command == "results":
        r = api.get_results()
        if r.get("ok"):
            for p in r.get("results", []):
                print(f"  [{p.get('index','?')}] {p.get('title','')[:70]}")
                print(f"      {p.get('authors','')[:70]}")
                print()

    elif args.command == "next":
        r = api.next_page()
        print(f"  {GREEN}Next page: {r.get('count',0)} results{RESET}" if r.get("ok")
              else f"  {RED}Error:{RESET} {r.get('error','?')}")

    elif args.command == "prev":
        r = api.prev_page()
        print(f"  {GREEN}Previous page: {r.get('count',0)} results{RESET}" if r.get("ok")
              else f"  {RED}Error:{RESET} {r.get('error','?')}")

    elif args.command == "open":
        r = api.open_paper(index=args.index)
        print(f"  {GREEN}Opened:{RESET} {r.get('title','?')[:60]}" if r.get("ok")
              else f"  {RED}Error:{RESET} {r.get('error','?')}")

    elif args.command == "save":
        r = api.save_paper(index=args.index)
        print(f"  {GREEN}Saved{RESET} paper #{args.index}" if r.get("ok")
              else f"  {RED}Error:{RESET} {r.get('error','?')}")

    elif args.command == "cite":
        r = api.cite_paper(index=args.index)
        if r.get("ok"):
            for k, v in r.get("citations", {}).items():
                if k == "download_formats":
                    print(f"  {BOLD}Download formats:{RESET}")
                    for fmt in v:
                        print(f"    - {fmt['name']}: {fmt['href'][:60]}")
                else:
                    print(f"  {BOLD}{k}:{RESET} {str(v)[:120]}")

    elif args.command == "cited-by":
        r = api.cited_by(index=args.index)
        if r.get("ok"):
            print(f"  {GREEN}Papers citing #{args.index}: {r['count']} results{RESET}")
            for p in r.get("results", [])[:5]:
                print(f"    - {p.get('title','')[:60]}")

    elif args.command == "pdf":
        r = api.get_pdf_url(index=args.index)
        print(f"  {GREEN}PDF:{RESET} {r.get('url','?')}" if r.get("ok")
              else f"  {YELLOW}No PDF available{RESET} for result #{args.index}")

    elif args.command == "filter":
        if args.time_filter:
            r = api.filter_time(year=args.time_filter)
            if r.get("ok"):
                print(f"  {GREEN}Filtered:{RESET} {r.get('filter','')}")
        if args.sort:
            r = api.filter_sort(order=args.sort)
            if r.get("ok"):
                print(f"  {GREEN}Sorted:{RESET} {r.get('sort','')}")

    elif args.command == "profile":
        r = api.open_profile()
        if r.get("ok"):
            p = r.get("profile", {})
            print(f"  {BOLD}{p.get('name','?')}{RESET}")
            print(f"  {p.get('affiliation','')}")
            if p.get("interests"):
                print(f"  Interests: {', '.join(p['interests'])}")

    elif args.command == "library":
        r = api.open_library()
        if r.get("ok"):
            print(f"  {GREEN}Library: {r['count']} papers{RESET}")
            for p in r.get("results", []):
                print(f"  - {p.get('title','')[:70]}")

    elif args.command == "author":
        name = " ".join(args.name)
        r = api.search_author(name)
        if r.get("ok"):
            for a in r.get("authors", []):
                print(f"  {BOLD}{a.get('name','?')}{RESET}")
                print(f"    {a.get('affiliation','')}")
                print(f"    {a.get('cited','')}")
                print()

    elif args.command == "screenshot":
        r = api.screenshot(output_path=args.output)
        print(f"  {GREEN}Saved:{RESET} {r.get('path','?')}" if r.get("ok")
              else f"  {RED}Error:{RESET} {r.get('error','?')}")


if __name__ == "__main__":
    main()
