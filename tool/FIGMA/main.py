#!/usr/bin/env python3
"""FIGMA - Figma design tool automation via CDMCP."""
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists(): break
    _r = _r.parent
sys.path.insert(0, str(_r))
from logic.resolve import setup_paths
setup_paths(__file__)

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("FIGMA")

    parser = argparse.ArgumentParser(
        description="Figma design automation via CDMCP",
        epilog="MCP commands use --mcp- prefix: e.g., FIGMA --mcp-boot, FIGMA --mcp-rectangle --x 400 --y 300",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("boot", help="Boot Figma session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Manually trigger recovery")
    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("files", help="List design files")
    sub.add_parser("layers", help="List layers in current file")
    sub.add_parser("home", help="Navigate to Figma home")

    p_open = sub.add_parser("open", help="Open a design file")
    p_open.add_argument("title", help="File title to open")

    p_shot = sub.add_parser("screenshot", help="Take a screenshot")
    p_shot.add_argument("--output", default=None, help="Output file path")

    p_create = sub.add_parser("create", help="Create a new file")
    p_create.add_argument("type", nargs="?", default="design",
                          choices=["design", "figjam", "slides"],
                          help="File type (default: design)")

    p_zoom = sub.add_parser("zoom", help="Zoom canvas")
    p_zoom.add_argument("level", nargs="?", default="fit",
                        help="in, out, fit, or percentage (50, 100, 200)")

    p_tool = sub.add_parser("tool", help="Select a tool")
    p_tool.add_argument("name", choices=["move", "frame", "rectangle",
                                         "ellipse", "line", "pen", "text", "hand"])

    p_rect = sub.add_parser("rectangle", help="Draw a rectangle")
    p_rect.add_argument("--x", type=int, default=400)
    p_rect.add_argument("--y", type=int, default=300)
    p_rect.add_argument("--width", type=int, default=100)
    p_rect.add_argument("--height", type=int, default=100)

    p_text = sub.add_parser("text", help="Add text to canvas")
    p_text.add_argument("content", help="Text to add")
    p_text.add_argument("--x", type=int, default=400)
    p_text.add_argument("--y", type=int, default=300)

    sub.add_parser("undo", help="Undo last action")
    sub.add_parser("redo", help="Redo last undone action")

    p_rename = sub.add_parser("rename", help="Rename current file")
    p_rename.add_argument("name", help="New file name")

    sub.add_parser("export", help="Open export dialog")

    p_ellipse = sub.add_parser("ellipse", help="Draw an ellipse")
    p_ellipse.add_argument("--x", type=int, default=400)
    p_ellipse.add_argument("--y", type=int, default=300)
    p_ellipse.add_argument("--width", type=int, default=100)
    p_ellipse.add_argument("--height", type=int, default=100)

    p_line = sub.add_parser("line", help="Draw a line")
    p_line.add_argument("--x1", type=int, default=400)
    p_line.add_argument("--y1", type=int, default=300)
    p_line.add_argument("--x2", type=int, default=550)
    p_line.add_argument("--y2", type=int, default=400)

    p_frame = sub.add_parser("frame", help="Draw a frame")
    p_frame.add_argument("--x", type=int, default=400)
    p_frame.add_argument("--y", type=int, default=200)
    p_frame.add_argument("--width", type=int, default=200)
    p_frame.add_argument("--height", type=int, default=200)

    sub.add_parser("select-all", help="Select all objects")
    sub.add_parser("copy", help="Copy selection")
    sub.add_parser("paste", help="Paste from clipboard")
    sub.add_parser("duplicate", help="Duplicate selection")
    sub.add_parser("delete", help="Delete selection")
    sub.add_parser("group", help="Group selected objects")
    sub.add_parser("ungroup", help="Ungroup selected objects")
    sub.add_parser("deselect", help="Deselect all objects")

    p_color = sub.add_parser("color", help="Change fill color of selection")
    p_color.add_argument("hex", help="Hex color (e.g. FF5733)")

    p_move = sub.add_parser("move", help="Move selection by offset")
    p_move.add_argument("--dx", type=int, default=0)
    p_move.add_argument("--dy", type=int, default=0)

    p_click = sub.add_parser("click", help="Click at canvas position")
    p_click.add_argument("--x", type=int, required=True)
    p_click.add_argument("--y", type=int, required=True)
    p_click.add_argument("--double", action="store_true")

    p_resize = sub.add_parser("resize", help="Resize selection to exact dimensions")
    p_resize.add_argument("--width", type=int, required=True)
    p_resize.add_argument("--height", type=int, required=True)

    p_rotate = sub.add_parser("rotate", help="Rotate selection by degrees")
    p_rotate.add_argument("--degrees", type=float, required=True)

    p_stroke = sub.add_parser("stroke", help="Add stroke to selection")
    p_stroke.add_argument("--color", default="#000000")
    p_stroke.add_argument("--width", type=int, default=2)

    p_rlayer = sub.add_parser("rename-layer", help="Rename a layer")
    p_rlayer.add_argument("old_name")
    p_rlayer.add_argument("new_name")

    p_mode = sub.add_parser("mode", help="Switch right-panel tab")
    p_mode.add_argument("name", choices=["design", "prototype"])

    sub.add_parser("close", help="Close file and return to home")
    sub.add_parser("editor-info", help="Identify editor areas")

    sub.add_parser("create-component", help="Create component from selection")
    sub.add_parser("detach-instance", help="Detach component instance")
    sub.add_parser("auto-layout", help="Add auto layout to selection")

    p_comment = sub.add_parser("comment", help="Add a comment")
    p_comment.add_argument("--text", required=True)
    p_comment.add_argument("--x", type=int, required=True)
    p_comment.add_argument("--y", type=int, required=True)

    p_radius = sub.add_parser("corner-radius", help="Set corner radius")
    p_radius.add_argument("radius", type=int)

    sub.add_parser("plugins", help="Open plugins menu")

    p_tab = sub.add_parser("panel-tab", help="Switch right-panel tab (design/prototype)")
    p_tab.add_argument("tab", choices=["design", "prototype"])

    sub.add_parser("add-export", help="Add export setting to selection")
    sub.add_parser("properties", help="Read right-panel property values")

    p_qa = sub.add_parser("quick-actions", help="Open Figma Quick Actions (Cmd+/)")
    p_qa.add_argument("--query", default="")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.FIGMA.logic.chrome import api

    def _ok(msg): print(f"  {BOLD}{GREEN}{msg}{RESET}")
    def _err(r): print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    if args.command == "boot":
        r = api.boot_session()
        if r.get("ok"):
            _ok("Booted" if r.get("action") != "already_booted" else "Session already_booted")
            print(f"  State: {r.get('state', '?')}")
        else: _err(r)

    elif args.command == "session":
        s = api.get_session_status()
        print(f"  State: {BOLD}{s.get('state', '?')}{RESET}")
        print(f"  Active: {'Yes' if s.get('session_active') else 'No'}")
        if s.get("last_url"): print(f"  URL: {s['last_url'][:60]}")
        if s.get("last_file_name"): print(f"  File: {s['last_file_name']}")

    elif args.command == "recover":
        r = api._recover()
        _ok("Recovered") if r else print(f"  {BOLD}{RED}Recovery failed{RESET}.")

    elif args.command == "status":
        r = api.get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")

    elif args.command == "page":
        r = api.get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else: _err(r)

    elif args.command == "files":
        r = api.list_files()
        if r.get("ok"):
            files = r.get("files", [])
            print(f"  Found {r.get('count', 0)} files:")
            for i, f in enumerate(files):
                print(f"    [{i+1}] {f.get('title', '?'):<50} {f.get('modified', '')}")
        else: _err(r)

    elif args.command == "open":
        r = api.open_file(args.title)
        if r.get("ok"):
            _ok(f"Opened '{args.title}'")
            print(f"  URL: {r.get('url', '?')}")
        else: _err(r)

    elif args.command == "layers":
        r = api.get_layers()
        if r.get("ok"):
            layers = r.get("layers", [])
            print(f"  Found {r.get('count', 0)} layers:")
            for l in layers:
                print(f"    {l.get('name', '?')}")
        else: _err(r)

    elif args.command == "home":
        r = api.navigate_home()
        if r.get("ok"): _ok("Navigated to home.")
        else: _err(r)

    elif args.command == "screenshot":
        r = api.take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Saved{RESET} {r['path']} ({r['size']} bytes)")
        else: _err(r)

    elif args.command == "create":
        r = api.create_file(args.type)
        if r.get("ok"):
            _ok(f"Created {args.type} file")
            print(f"  URL: {r.get('url', '?')}")
        else: _err(r)

    elif args.command == "zoom":
        r = api.zoom(args.level)
        if r.get("ok"): _ok(f"Zoomed to {args.level}")
        else: _err(r)

    elif args.command == "tool":
        r = api.select_tool(args.name)
        if r.get("ok"): _ok(f"Selected {args.name} tool")
        else: _err(r)

    elif args.command == "rectangle":
        r = api.draw_rectangle(args.x, args.y, args.width, args.height)
        if r.get("ok"): _ok(f"Drew rectangle at ({args.x}, {args.y})")
        else: _err(r)

    elif args.command == "text":
        r = api.add_text(args.content, args.x, args.y)
        if r.get("ok"): _ok(f"Added text at ({args.x}, {args.y})")
        else: _err(r)

    elif args.command == "undo":
        r = api.undo()
        if r.get("ok"): _ok("Undone")
        else: _err(r)

    elif args.command == "redo":
        r = api.redo()
        if r.get("ok"): _ok("Redone")
        else: _err(r)

    elif args.command == "rename":
        r = api.rename_file(args.name)
        if r.get("ok"): _ok(f"Renamed to '{args.name}'")
        else: _err(r)

    elif args.command == "export":
        r = api.export()
        if r.get("ok"): _ok("Export dialog opened")
        else: _err(r)

    elif args.command == "ellipse":
        r = api.draw_ellipse(args.x, args.y, args.width, args.height)
        if r.get("ok"): _ok(f"Drew ellipse at ({args.x}, {args.y})")
        else: _err(r)

    elif args.command == "line":
        r = api.draw_line(args.x1, args.y1, args.x2, args.y2)
        if r.get("ok"): _ok(f"Drew line from ({args.x1},{args.y1}) to ({args.x2},{args.y2})")
        else: _err(r)

    elif args.command == "frame":
        r = api.draw_frame(args.x, args.y, args.width, args.height)
        if r.get("ok"): _ok(f"Drew frame at ({args.x}, {args.y})")
        else: _err(r)

    elif args.command == "select-all":
        r = api.select_all()
        if r.get("ok"): _ok("Selected all")
        else: _err(r)

    elif args.command == "copy":
        r = api.copy_selection()
        if r.get("ok"): _ok("Copied")
        else: _err(r)

    elif args.command == "paste":
        r = api.paste_selection()
        if r.get("ok"): _ok("Pasted")
        else: _err(r)

    elif args.command == "duplicate":
        r = api.duplicate_selection()
        if r.get("ok"): _ok("Duplicated")
        else: _err(r)

    elif args.command == "delete":
        r = api.delete_selection()
        if r.get("ok"): _ok("Deleted")
        else: _err(r)

    elif args.command == "group":
        r = api.group_selection()
        if r.get("ok"): _ok("Grouped")
        else: _err(r)

    elif args.command == "ungroup":
        r = api.ungroup_selection()
        if r.get("ok"): _ok("Ungrouped")
        else: _err(r)

    elif args.command == "deselect":
        r = api.deselect()
        if r.get("ok"): _ok("Deselected")
        else: _err(r)

    elif args.command == "color":
        r = api.change_fill_color(args.hex)
        if r.get("ok"): _ok(f"Changed color to #{args.hex}")
        else: _err(r)

    elif args.command == "move":
        r = api.move_selection(dx=args.dx, dy=args.dy)
        if r.get("ok"): _ok(f"Moved by ({args.dx}, {args.dy})")
        else: _err(r)

    elif args.command == "click":
        r = api.click_canvas(args.x, args.y, double=args.double)
        if r.get("ok"): _ok(f"Clicked at ({args.x}, {args.y})")
        else: _err(r)

    elif args.command == "resize":
        r = api.resize_selection(args.width, args.height)
        if r.get("ok"): _ok(f"Resized to {args.width}x{args.height}")
        else: _err(r)

    elif args.command == "rotate":
        r = api.rotate_selection(args.degrees)
        if r.get("ok"): _ok(f"Rotated to {args.degrees} degrees")
        else: _err(r)

    elif args.command == "stroke":
        r = api.add_stroke(args.color, args.width)
        if r.get("ok"): _ok(f"Added stroke {args.color} {args.width}px")
        else: _err(r)

    elif args.command == "rename-layer":
        r = api.rename_layer(args.old_name, args.new_name)
        if r.get("ok"): _ok(f"Renamed '{args.old_name}' to '{args.new_name}'")
        else: _err(r)

    elif args.command == "mode":
        r = api.switch_mode(args.name)
        if r.get("ok"): _ok(f"Switched to {args.name} mode")
        else: _err(r)

    elif args.command == "close":
        r = api.close_file()
        if r.get("ok"): _ok("Closed file")
        else: _err(r)

    elif args.command == "editor-info":
        r = api.get_editor_info()
        if r.get("ok"):
            info = r.get("info", {})
            print(f"  Title: {info.get('title', '?')}")
            print(f"  Canvas: {'visible' if info.get('canvas', {}).get('visible') else 'not found'}")
            print(f"  Layers: {'visible' if info.get('layers_panel', {}).get('visible') else 'not found'}")
            print(f"  Properties: {'visible' if info.get('properties_panel', {}).get('visible') else 'not found'}")
        else: _err(r)

    elif args.command == "create-component":
        r = api.create_component()
        if r.get("ok"): _ok("Created component")
        else: _err(r)

    elif args.command == "detach-instance":
        r = api.detach_instance()
        if r.get("ok"): _ok("Detached instance")
        else: _err(r)

    elif args.command == "auto-layout":
        r = api.auto_layout()
        if r.get("ok"): _ok("Added auto layout")
        else: _err(r)

    elif args.command == "comment":
        r = api.add_comment(args.text, args.x, args.y)
        if r.get("ok"): _ok(f"Added comment: {args.text}")
        else: _err(r)

    elif args.command == "corner-radius":
        r = api.set_corner_radius(args.radius)
        if r.get("ok"): _ok(f"Set corner radius to {args.radius}px")
        else: _err(r)

    elif args.command == "plugins":
        r = api.open_plugins_menu()
        if r.get("ok"):
            _ok("Plugins menu opened")
            for item in r.get("items", []):
                print(f"    - {item}")
        else: _err(r)

    elif args.command == "panel-tab":
        r = api.switch_panel_tab(args.tab)
        if r.get("ok"): _ok(f"Switched to {args.tab} tab")
        else: _err(r)

    elif args.command == "add-export":
        r = api.add_export_setting()
        if r.get("ok"): _ok("Added export setting")
        else: _err(r)

    elif args.command == "properties":
        r = api.get_panel_properties()
        if r.get("ok"):
            props = r.get("properties", {})
            if props:
                for k, v in props.items():
                    print(f"    {k}: {v}")
            else:
                print("    No properties visible (select an element first)")
        else: _err(r)

    elif args.command == "quick-actions":
        r = api.open_quick_actions(args.query)
        if r.get("ok"): _ok(f"Quick Actions opened{' with query: ' + args.query if args.query else ''}")
        else: _err(r)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
