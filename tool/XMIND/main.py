#!/usr/bin/env python3
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
from logic.interface.config import get_color


def main():
    tool = ToolBase("XMIND")

    parser = argparse.ArgumentParser(
        description="XMind mind mapping via CDMCP", add_help=False
    )
    sub = parser.add_subparsers(dest="command", help="Subcommand")

    sub.add_parser("status", help="Check authentication state")
    sub.add_parser("page", help="Show current page info")
    sub.add_parser("maps", help="List mind maps (requires auth)")
    sub.add_parser("sidebar", help="Show sidebar sections (requires auth)")
    sub.add_parser("boot", help="Boot XMind CDMCP session in dedicated window")
    sub.add_parser("session", help="Show session and state machine status")
    sub.add_parser("recover", help="Manually trigger recovery")

    p_create = sub.add_parser("create", help="Create a new mind map")
    p_create.add_argument("title", nargs="?", default="New Mind Map",
                          help="Title for the new map")

    p_open = sub.add_parser("open", help="Open an existing mind map")
    p_open.add_argument("title", help="Title of the map to open")

    p_add = sub.add_parser("add-node", help="Add a node to the mind map")
    p_add.add_argument("text", help="Text for the new node")
    p_add.add_argument("--parent", default=None, help="Parent node text to attach to")
    p_add.add_argument("--sibling", action="store_true", help="Add as sibling instead of child")

    p_edit = sub.add_parser("edit-node", help="Edit a node's text")
    p_edit.add_argument("node_text", help="Current text of the node to edit")
    p_edit.add_argument("new_text", help="New text for the node")

    p_del = sub.add_parser("delete-node", help="Delete a node")
    p_del.add_argument("node_text", help="Text of the node to delete")

    sub.add_parser("nodes", help="List all visible nodes in the mind map")
    sub.add_parser("home", help="Navigate to XMind home page")

    p_shot = sub.add_parser("screenshot", help="Take a screenshot")
    p_shot.add_argument("--output", default=None, help="Output file path")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    BLUE = get_color("BLUE")
    RESET = get_color("RESET")

    from tool.XMIND.logic.chrome.api import (
        get_auth_state, get_page_info, get_maps, get_sidebar,
        boot_session, get_session_status, create_map, open_map,
        add_node, edit_node, delete_node, take_screenshot,
        navigate_home, get_map_nodes,
        _recover,
    )

    if args.command == "boot":
        r = boot_session()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Booted{RESET} XMind session.")
            print(f"  State: {r.get('state', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET} to boot: {r.get('error', '?')}")

    elif args.command == "session":
        s = get_session_status()
        print(f"  State: {BOLD}{s.get('state', '?')}{RESET}")
        print(f"  Active: {'Yes' if s.get('session_active') else 'No'}")
        if s.get("last_url"):
            print(f"  URL: {s['last_url'][:60]}")
        if s.get("last_map_title"):
            print(f"  Map: {s['last_map_title']}")
        if s.get("error"):
            print(f"  Error: {RED}{s['error']}{RESET}")

    elif args.command == "recover":
        from tool.XMIND.logic.chrome.api import _recover as do_recover
        r = do_recover()
        if r:
            print(f"  {BOLD}{GREEN}Recovered{RESET} XMind session.")
        else:
            print(f"  {BOLD}{RED}Recovery failed{RESET}.")

    elif args.command == "status":
        r = get_auth_state()
        auth = r.get("authenticated", False)
        print(f"  Authenticated: {BOLD}{GREEN if auth else YELLOW}{'Yes' if auth else 'No'}{RESET}")
        print(f"  Page: {r.get('title', '?')}")
        if r.get("isLogin"):
            print(f"  {YELLOW}On login page{RESET}")

    elif args.command == "page":
        r = get_page_info()
        if r.get("ok"):
            print(f"  Title:   {r.get('title', '?')}")
            print(f"  URL:     {r.get('url', '?')}")
            print(f"  Section: {r.get('section', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET} to get page info: {r.get('error', '?')}")

    elif args.command == "maps":
        r = get_maps()
        if r.get("ok"):
            maps = r.get("maps", [])
            print(f"  Found {r.get('count', 0)} maps.")
            for i, m in enumerate(maps):
                print(f"  [{i+1}] {m['title']:<50} {m.get('time','')}")
            if not maps:
                print(f"  {YELLOW}No maps visible.{RESET}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "sidebar":
        r = get_sidebar()
        if r.get("ok"):
            for s in r.get("sections", []):
                print(f"  {s}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "create":
        r = create_map(args.title)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Created{RESET} mind map.")
            print(f"  URL: {r.get('url', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "open":
        r = open_map(args.title)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Opened{RESET} '{args.title}'.")
            print(f"  URL: {r.get('url', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "add-node":
        r = add_node(parent_text=args.parent, text=args.text, as_child=not args.sibling)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Added{RESET} node: {args.text}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "edit-node":
        r = edit_node(args.node_text, args.new_text)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Edited{RESET} '{args.node_text}' -> '{args.new_text}'")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "delete-node":
        r = delete_node(args.node_text)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Deleted{RESET} node: {args.node_text}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "nodes":
        r = get_map_nodes()
        if r.get("ok"):
            nodes = r.get("nodes", [])
            print(f"  Found {r.get('count', 0)} nodes:")
            for i, n in enumerate(nodes):
                print(f"    [{i+1}] {n.get('text', '?')}")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "home":
        r = navigate_home()
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Navigated{RESET} to home.")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    elif args.command == "screenshot":
        r = take_screenshot(output_path=args.output)
        if r.get("ok"):
            print(f"  {BOLD}{GREEN}Screenshot saved:{RESET} {r['path']} ({r['size']} bytes)")
        else:
            print(f"  {BOLD}{RED}Failed{RESET}: {r.get('error', '?')}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
