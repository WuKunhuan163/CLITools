#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import MCPToolBase
from interface.config import get_color


def main():
    tool = MCPToolBase("CHARTCUBE", session_name="chartcube")

    parser = argparse.ArgumentParser(
        description="ChartCube chart generation via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., CHARTCUBE --mcp-boot",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand")

    sub.add_parser("boot", help="Boot ChartCube CDMCP session")
    sub.add_parser("status", help="Check current page state and workflow step")
    sub.add_parser("page", help="Get detailed page info")
    sub.add_parser("scan", help="Scan page for interactive elements")
    sub.add_parser("session", help="Show CDMCP session status")
    sub.add_parser("state", help="Get comprehensive MCP state")

    p_nav = sub.add_parser("go", help="Navigate to a wizard step")
    p_nav.add_argument("step", choices=["upload", "guide", "make", "export", "home"])

    p_sample = sub.add_parser("sample", help="Select a sample dataset")
    p_sample.add_argument("index", type=int, nargs="?", default=0, help="Sample index (0-2)")

    sub.add_parser("next", help="Click the 'Next Step' button")

    p_chart = sub.add_parser("chart", help="Select a chart type")
    p_chart.add_argument("name", help="Chart name (e.g. '柱状图', '折线图')")

    sub.add_parser("generate", help="Click 'Generate Chart' button")
    sub.add_parser("start", help="Click '立即制作图表' from home page")

    p_cols = sub.add_parser("columns", help="Select data columns on upload page")
    p_cols.add_argument("cols", nargs="?", default="all", help="'all' or comma-separated column names")

    p_export = sub.add_parser("export", help="Export the chart")
    p_export.add_argument("format", nargs="?", default="all",
                          choices=["all", "image", "data", "code", "config"])
    sub.add_parser("get-code", help="Extract G2Plot code from export page")
    sub.add_parser("get-config", help="Extract chart config JSON from export page")

    p_toggle = sub.add_parser("toggle", help="Toggle a chart option (e.g. 平滑, 显示点, 显示标签)")
    p_toggle.add_argument("option", help="Option label (e.g. '平滑', '显示点', '显示标签')")

    p_title = sub.add_parser("title", help="Set the chart title")
    p_title.add_argument("text", help="New title text")

    p_size = sub.add_parser("size", help="Set canvas size")
    p_size.add_argument("width", type=int, help="Width in pixels")
    p_size.add_argument("height", type=int, help="Height in pixels")

    sub.add_parser("export-all", help="Click 'Export All' on export page")
    sub.add_parser("list-charts", help="List all chart types (must be on guide page)")

    p_desc = sub.add_parser("description", help="Set the chart description")
    p_desc.add_argument("text", help="New description text")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    get_color("YELLOW")
    RESET = get_color("RESET")

    from tool.CHARTCUBE.logic.utils.chrome.api import (
        boot_session, get_status, get_page_info, navigate_step,
        use_sample_data, click_next, select_chart_type,
        generate_chart, scan_elements, select_columns,
        export_chart, start_chart, get_code, get_config,
        toggle_option, set_title, set_canvas_size,
        export_all, list_chart_types, set_description,
    )

    if args.command == "boot":
        r = boot_session()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Booted{RESET} ChartCube session.")
            print(f"  Action: {r.get('action', '?')}")
            if r.get("url"):
                print(f"  URL: {r['url']}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET} to boot: {r.get('error', '?')}")

    elif args.command == "status":
        r = get_status()
        if r.get("ok"):
            step_names = {
                "home": "Home",
                "upload": "Step 1: Upload Data",
                "guide": "Step 2: Select Chart",
                "make": "Step 3: Configure Chart",
                "export": "Step 4: Export Chart",
            }
            step = r.get("step", "unknown")
            print(f"  {BOLD}Step{RESET}: {step_names.get(step, step)}")
            print(f"  URL: {r.get('url', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title: {r.get('title', '?')}")
            print(f"  Path: {r.get('path', '?')}")
            btns = r.get("buttons", [])
            if btns:
                print(f"  Buttons ({len(btns)}):")
                for b in btns[:10]:
                    print(f"    - {b}")
            headings = r.get("headings", [])
            if headings:
                print(f"  Headings ({len(headings)}):")
                for h in headings[:10]:
                    print(f"    - {h}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "scan":
        r = scan_elements()
        if r.get("ok"):
            elements = r.get("elements", [])
            print(f"  Found {r.get('count', 0)} interactive elements:")
            for el in elements:
                tag = el.get("tag", "?")
                etype = el.get("type", "")
                text = el.get("text", "")[:40]
                rect = el.get("rect", {})
                pos = f"({rect.get('x',0)},{rect.get('y',0)})"
                print(f"    <{tag}> {etype:10s} {pos:12s} {text}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "go":
        r = navigate_step(args.step)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Navigated{RESET} to {args.step}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "sample":
        r = use_sample_data(args.index)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Selected{RESET} sample #{args.index}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "next":
        r = click_next()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Clicked{RESET} '{r.get('clicked', 'Next')}'")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "chart":
        r = select_chart_type(args.name)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Selected{RESET} chart: {r.get('selected', args.name)}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "generate":
        r = generate_chart()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Generated{RESET} chart")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "start":
        r = start_chart()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Started{RESET} chart wizard")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "columns":
        r = select_columns(args.cols)
        if r.get("ok"):
            clicked = r.get("clicked", r.get("action", "done"))
            print(f"  {BOLD}{GREEN}Selected{RESET} columns: {clicked}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "export":
        r = export_chart(args.format)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Exported{RESET} ({args.format}): {r.get('clicked', 'done')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "get-code":
        r = get_code()
        if r.get("ok"):
            print(r.get("code", ""))
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "get-config":
        r = get_config()
        if r.get("ok"):
            print(r.get("config", ""))
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "toggle":
        r = toggle_option(args.option)
        if r.get("ok"):
            was = r.get("was", "?")
            now = r.get("now", "?")
            print(f"  {BOLD}{GREEN}Toggled{RESET} '{args.option}': {was} -> {now}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "title":
        r = set_title(args.text)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Set title{RESET}: {r.get('title', args.text)}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "size":
        r = set_canvas_size(args.width, args.height)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Set size{RESET}: {r.get('width', args.width)}x{r.get('height', args.height)}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "export-all":
        r = export_all()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Exported{RESET} all: {r.get('clicked', 'done')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "list-charts":
        r = list_chart_types()
        if r.get("ok"):
            cats = r.get("categories", [])
            charts = r.get("charts", [])
            print(f"  {BOLD}Categories{RESET} ({len(cats)}):")
            for c in cats:
                print(f"    - {c}")
            print(f"  {BOLD}Chart types{RESET} ({r.get('count', 0)}):")
            for c in charts:
                print(f"    - {c}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "description":
        r = set_description(args.text)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Set description{RESET}: {r.get('description', args.text)}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "session" or args.command == "state":
        tool.print_mcp_state()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
