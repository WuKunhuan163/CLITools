#!/usr/bin/env python3
"""LUCIDCHART - Lucidchart diagramming automation via CDMCP."""
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


def main():
    tool = MCPToolBase("LUCIDCHART", session_name="lucidchart")

    parser = argparse.ArgumentParser(
        description="Lucidchart diagramming automation via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., LUCIDCHART --mcp-boot, LUCIDCHART --mcp-navigate home",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    # Session & status
    sub.add_parser("boot", help="Boot Lucidchart session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Recover from error state")
    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("state", help="Get comprehensive MCP state")
    sub.add_parser("layout", help="Identify editor layout areas")

    # Navigation
    p_nav = sub.add_parser("navigate", help="Navigate to section or URL")
    p_nav.add_argument("target", help="Section name or URL")
    sub.add_parser("back", help="Navigate back")
    sub.add_parser("new", help="Create new blank document")
    p_open = sub.add_parser("open", help="Open document by URL")
    p_open.add_argument("url", help="Document URL")
    p_open_name = sub.add_parser("open-doc", help="Open document by name")
    p_open_name.add_argument("name", help="Document title to match")
    p_tmpl = sub.add_parser("templates", help="Browse templates")
    p_tmpl.add_argument("category", nargs="?", help="Template category")
    p_docs = sub.add_parser("documents", help="List documents")
    p_docs.add_argument("--limit", type=int, default=20)

    # Screenshot
    p_shot = sub.add_parser("screenshot", help="Capture page screenshot")
    p_shot.add_argument("--output", help="Output file path")

    # Editor operations
    sub.add_parser("select-all", help="Select all objects (Cmd+A)")
    sub.add_parser("delete", help="Delete selected objects")
    sub.add_parser("copy", help="Copy selected objects (Cmd+C)")
    sub.add_parser("paste", help="Paste from clipboard (Cmd+V)")
    sub.add_parser("undo", help="Undo last action (Cmd+Z)")
    sub.add_parser("redo", help="Redo last action (Cmd+Shift+Z)")
    sub.add_parser("group", help="Group selected objects (Cmd+G)")
    sub.add_parser("ungroup", help="Ungroup selected objects (Cmd+Shift+G)")
    sub.add_parser("escape", help="Press Escape")
    p_zoom = sub.add_parser("zoom", help="Zoom canvas")
    p_zoom.add_argument("level", nargs="?", help="in, out, fit, reset, or percentage")
    sub.add_parser("zoom-level", help="Show current zoom level")

    # Shape & drawing operations
    p_shape = sub.add_parser("add-shape", help="Add shape from library to canvas")
    p_shape.add_argument("shape", help="Shape name (e.g. Process, Decision, Rectangle)")
    p_shape.add_argument("--x", type=int, help="X position")
    p_shape.add_argument("--y", type=int, help="Y position")
    p_text = sub.add_parser("add-text", help="Add text block to canvas")
    p_text.add_argument("text", help="Text content")
    p_text.add_argument("--x", type=int, help="X position")
    p_text.add_argument("--y", type=int, help="Y position")
    p_click = sub.add_parser("click", help="Click at canvas position")
    p_click.add_argument("x", type=int, help="X coordinate")
    p_click.add_argument("y", type=int, help="Y coordinate")
    p_line = sub.add_parser("draw-line", help="Draw line between two points")
    p_line.add_argument("x1", type=int)
    p_line.add_argument("y1", type=int)
    p_line.add_argument("x2", type=int)
    p_line.add_argument("y2", type=int)
    p_fill = sub.add_parser("fill-color", help="Set fill color for selected object")
    p_fill.add_argument("color", help="Hex color (e.g. #FF0000)")
    p_tb = sub.add_parser("toolbar", help="Click a toolbar button by title")
    p_tb.add_argument("button", help="Button title attribute")
    p_rename = sub.add_parser("rename", help="Rename current document")
    p_rename.add_argument("name", help="New document name")

    # Page & info operations
    sub.add_parser("pages", help="List pages in document")
    sub.add_parser("add-page", help="Add new page")
    sub.add_parser("shapes", help="List available shapes in library")
    sub.add_parser("shape-libraries", help="List shape library sections")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    B = get_color("BOLD")
    G = get_color("GREEN")
    R = get_color("RED")
    Y = get_color("YELLOW")
    E = get_color("RESET")

    from tool.LUCIDCHART.logic.chrome import api

    if args.command == "boot":
        r = api.boot_session()
        if r.get("ok"):
            print(f"  {B}{G}Session {r.get('action', 'booted')}{E}")
            print(f"  State: {r.get('state', '?')}")
        else:
            print(f"  {B}{R}Boot failed{E}: {r.get('error')}")

    elif args.command == "session":
        r = api.get_session_status()
        st = r.get("state", "?")
        c = G if st == "idle" else (Y if st in ("navigating", "editing") else R)
        print(f"  State:   {B}{c}{st}{E}")
        print(f"  Session: {'alive' if r.get('session_alive') else 'none'}")
        print(f"  CDP:     {'ok' if r.get('cdp_available') else 'unavail'}")
        if r.get("last_url"): print(f"  URL:     {r['last_url'][:80]}")

    elif args.command == "recover":
        r = api._recover()
        print(f"  {B}{G}Recovered{E}" if r.get("ok") else f"  {R}Failed: {r.get('error')}{E}")

    elif args.command == "status":
        r = api.get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Auth: {B}{G if auth else Y}{'Yes' if auth else 'No'}{E}")
        if r.get("username"): print(f"  User: {r['username']}")

    elif args.command == "page":
        r = api.get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')[:80]}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "state":
        r = api.get_mcp_state()
        if r.get("ok"):
            print(f"  {B}URL:{E}       {r.get('url', '?')[:80]}")
            print(f"  {B}Section:{E}   {r.get('section', '?')}")
            print(f"  {B}Canvas:{E}    {'yes' if r.get('has_canvas') else 'no'}")
            print(f"  {B}Pages:{E}     {r.get('page_count', '?')}")
            print(f"  {B}Auth:{E}      {'Yes' if r.get('authenticated') else 'No'}")
            ms = r.get("machine_state", {})
            print(f"  {B}Machine:{E}   {ms.get('state', '?')}")
        else:
            print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "layout":
        r = api.get_editor_layout()
        if r.get("ok"):
            for area in r.get("areas", []):
                print(f"    - {area}")
            items = r.get("toolbar_items", [])
            if items: print(f"  Toolbar: {', '.join(items[:10])}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "navigate":
        r = api.navigate(args.target)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to {r.get('target')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "back":
        r = api.go_back()
        if r.get("ok"): print(f"  {B}{G}Navigated back{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "new":
        r = api.create_new_document()
        if r.get("ok"): print(f"  {B}{G}Created{E} new document: {r.get('url', '')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "open":
        r = api.open_document(args.url)
        if r.get("ok"): print(f"  {B}{G}Opened{E} {r.get('url', '')[:80]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "open-doc":
        r = api.open_document_by_name(args.name)
        if r.get("ok"): print(f"  {B}{G}Opened{E} '{r.get('document')}' at {r.get('url', '')[:60]}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "templates":
        r = api.navigate_templates(category=args.category)
        if r.get("ok"): print(f"  {B}{G}Navigated{E} to templates")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "documents":
        r = api.get_documents_list(limit=args.limit)
        if r.get("ok"):
            print(f"  Documents: {r.get('count', 0)}")
            for d in r.get("documents", []):
                mod = f" ({d['modified']})" if d.get("modified") else ""
                print(f"  [{d['index']}] {d.get('title', '?')[:60]}{mod}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "screenshot":
        r = api.take_screenshot(output_path=args.output)
        if r.get("ok"): print(f"  {B}{G}Saved{E} {r['path']} ({r['size']} bytes)")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "select-all":
        r = api.select_all()
        if r.get("ok"): print(f"  {B}{G}Selected all{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "delete":
        r = api.delete_selected()
        if r.get("ok"): print(f"  {B}{G}Deleted{E} selected")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "copy":
        r = api.copy_selected()
        if r.get("ok"): print(f"  {B}{G}Copied{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "paste":
        r = api.paste()
        if r.get("ok"): print(f"  {B}{G}Pasted{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "undo":
        r = api.undo()
        if r.get("ok"): print(f"  {B}{G}Undone{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "redo":
        r = api.redo()
        if r.get("ok"): print(f"  {B}{G}Redone{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "group":
        r = api.group_selected()
        if r.get("ok"): print(f"  {B}{G}Grouped{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "ungroup":
        r = api.ungroup_selected()
        if r.get("ok"): print(f"  {B}{G}Ungrouped{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "escape":
        r = api.escape()
        if r.get("ok"): print(f"  {B}{G}Escaped{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "zoom":
        r = api.zoom(level=args.level)
        if r.get("ok"): print(f"  {B}{G}Zoomed{E}: {r.get('action', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "zoom-level":
        r = api.get_zoom_level()
        if r.get("ok"): print(f"  Zoom: {r.get('zoom', '?')}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "add-shape":
        r = api.add_shape(args.shape, x=args.x, y=args.y)
        if r.get("ok"):
            pos = r.get("position", {})
            print(f"  {B}{G}Added{E} '{args.shape}' at ({pos.get('x','?')}, {pos.get('y','?')})")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "add-text":
        r = api.add_text(args.text, x=args.x, y=args.y)
        if r.get("ok"): print(f"  {B}{G}Added text{E}: \"{args.text}\"")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "click":
        r = api.click_canvas(args.x, args.y)
        if r.get("ok"): print(f"  {B}{G}Clicked{E} at ({args.x}, {args.y})")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "draw-line":
        r = api.draw_line(args.x1, args.y1, args.x2, args.y2)
        if r.get("ok"): print(f"  {B}{G}Drew line{E} ({args.x1},{args.y1}) -> ({args.x2},{args.y2})")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "fill-color":
        r = api.set_fill_color(args.color)
        if r.get("ok"): print(f"  {B}{G}Set fill{E} to {args.color}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "toolbar":
        r = api.toolbar_click(args.button)
        if r.get("ok"): print(f"  {B}{G}Clicked{E} '{args.button}'")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "rename":
        r = api.rename_document(args.name)
        if r.get("ok"): print(f"  {B}{G}Renamed{E} to '{args.name}'")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "pages":
        r = api.get_page_list()
        if r.get("ok"):
            for p in r.get("pages", []):
                print(f"    - {p}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "add-page":
        r = api.add_page()
        if r.get("ok"): print(f"  {B}{G}Added page{E}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "shapes":
        r = api.list_shapes_in_library()
        if r.get("ok"):
            shapes = r.get("shapes", [])
            print(f"  Shapes ({len(shapes)}):")
            for s in shapes:
                print(f"    - {s}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    elif args.command == "shape-libraries":
        r = api.list_shape_libraries()
        if r.get("ok"):
            for lib in r.get("libraries", []):
                print(f"    - {lib}")
        else: print(f"  {R}Error: {r.get('error')}{E}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
