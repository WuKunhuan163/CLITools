#!/usr/bin/env python3
"""SHOWDOC -- ShowDoc documentation platform via CDMCP.

Access ShowDoc API docs, data dictionaries, and team documentation
via Chrome DevTools MCP using the authenticated showdoc.com.cn session.

Usage:
    SHOWDOC boot                     Boot CDMCP session and open ShowDoc tab
    SHOWDOC status                   Check auth and session state
    SHOWDOC user                     Show authenticated user profile
    SHOWDOC projects                 List documentation projects
    SHOWDOC project <item_id>        Show project info and document tree
    SHOWDOC catalog <item_id>        Show catalog (folder tree)
    SHOWDOC page <page_id>           Show page content
    SHOWDOC goto <item_id> [page_id] Navigate to project or page in browser
    SHOWDOC home                     Navigate to dashboard
    SHOWDOC screenshot [--output]    Take screenshot of current page
"""
import sys
import argparse
from pathlib import Path

_r = Path(__file__).resolve().parent
while _r != _r.parent:
    if (_r / "bin" / "TOOL").exists():
        break
    _r = _r.parent
sys.path.insert(0, str(_r))
from interface.resolve import setup_paths
setup_paths(__file__)

from interface.tool import ToolBase
from interface.config import get_color

BOLD  = get_color("BOLD")
BLUE  = get_color("BLUE")
GREEN = get_color("GREEN")
RED   = get_color("RED")
YELLOW = get_color("YELLOW")
RESET = get_color("RESET")


def cmd_boot(args):
    from tool.SHOWDOC.logic.chrome.api import boot_session
    print(f"  {BOLD}{BLUE}Booting{RESET} ShowDoc CDMCP session...", flush=True)
    result = boot_session(args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} {result.get('action', 'booted')} ShowDoc session.", flush=True)
    else:
        print(f"  {BOLD}{RED}Failed{RESET} to boot: {result.get('error', 'Unknown error')}.", flush=True)


def cmd_status(args):
    from tool.SHOWDOC.logic.chrome.api import get_session_status, get_auth_state
    status = get_session_status(args.port)

    print(f"  {BOLD}Chrome CDP{RESET}: {'available' if status['cdp_available'] else 'unavailable'} (port {args.port})")
    print(f"  {BOLD}Session{RESET}: {'active' if status['session_active'] else 'inactive'}")

    if status["session_active"]:
        auth = get_auth_state(args.port)
        authed = auth.get("authenticated", False)
        label = f"{GREEN}authenticated{RESET}" if authed else f"{RED}not authenticated{RESET}"
        print(f"  {BOLD}Auth{RESET}: {label}")
        if auth.get("url"):
            print(f"  {BOLD}URL{RESET}: {auth['url']}")
        if authed and auth.get("user"):
            u = auth["user"]
            print(f"  {BOLD}User{RESET}: {u.get('username', 'N/A')} (uid {u.get('uid', '?')})")
        elif not authed:
            print(f"  Please log in to showdoc.com.cn in Chrome.")


def cmd_user(args):
    from tool.SHOWDOC.logic.chrome.api import get_user_info
    result = get_user_info(args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return
    u = result.get("user", {})
    print(f"  {BOLD}UID{RESET}: {u.get('uid', 'N/A')}")
    print(f"  {BOLD}Username{RESET}: {u.get('username', 'N/A')}")
    print(f"  {BOLD}Email{RESET}: {u.get('email', 'N/A')}")
    print(f"  {BOLD}Name{RESET}: {u.get('name', '') or '(not set)'}")
    vip = u.get("vip_type", 0)
    print(f"  {BOLD}VIP{RESET}: {'Yes' if vip else 'No'}")


def cmd_projects(args):
    from tool.SHOWDOC.logic.chrome.api import get_projects
    result = get_projects(args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return

    projects = result.get("projects", [])
    if not projects:
        print(f"  No projects found.")
        return

    print(f"  {BOLD}Projects{RESET} ({len(projects)}):")
    for p in projects:
        star = " *" if p.get("is_starred") else ""
        lock = " (private)" if p.get("is_private") else ""
        print(f"    [{p['item_id']}] {p['name']} ({p['type']}){lock}{star}")
        if p.get("description") and p["description"] != p["name"]:
            print(f"        {p['description'][:80]}")


def cmd_project(args):
    from tool.SHOWDOC.logic.chrome.api import get_project_info
    result = get_project_info(args.item_id, args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return

    proj = result.get("project", {})
    print(f"  {BOLD}Project{RESET}: {proj.get('item_name', 'N/A')}")
    print(f"  {BOLD}ID{RESET}: {proj.get('item_id', '?')}")

    type_map = {"1": "Regular", "4": "Table", "5": "Whiteboard"}
    print(f"  {BOLD}Type{RESET}: {type_map.get(proj.get('item_type', ''), proj.get('item_type', ''))}")

    menu = proj.get("menu", {})
    pages = menu.get("pages", [])
    catalogs = menu.get("catalogs", [])

    if pages:
        print(f"\n  {BOLD}Root Pages{RESET}:")
        for pg in pages:
            draft = " (draft)" if pg.get("is_draft") == "1" else ""
            print(f"    [{pg['page_id']}] {pg['page_title']}{draft}")

    def print_catalog(cat_list, indent=1):
        for cat in cat_list:
            prefix = "    " * indent
            print(f"{prefix}{BOLD}{cat['cat_name']}{RESET} (cat_id: {cat['cat_id']})")
            for pg in cat.get("pages", []):
                draft = " (draft)" if pg.get("is_draft") == "1" else ""
                print(f"{prefix}  [{pg['page_id']}] {pg['page_title']}{draft}")
            if cat.get("catalogs"):
                print_catalog(cat["catalogs"], indent + 1)

    if catalogs:
        print(f"\n  {BOLD}Catalogs{RESET}:")
        print_catalog(catalogs)


def cmd_catalog(args):
    from tool.SHOWDOC.logic.chrome.api import get_catalog
    result = get_catalog(args.item_id, args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return

    cats = result.get("catalogs", [])
    if not cats:
        print(f"  No catalogs found for project {args.item_id}.")
        return

    print(f"  {BOLD}Catalogs{RESET} for project {args.item_id}:")
    for c in cats:
        parent = f" (parent: {c['parent_cat_id']})" if c.get("parent_cat_id", "0") != "0" else ""
        print(f"    [{c['cat_id']}] {c['cat_name']} (level {c.get('level', '?')}){parent}")


def cmd_page(args):
    from tool.SHOWDOC.logic.chrome.api import get_page_content
    result = get_page_content(args.page_id, args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return

    pg = result.get("page", {})
    print(f"  {BOLD}Title{RESET}: {pg.get('title', 'N/A')}")
    print(f"  {BOLD}Page ID{RESET}: {pg.get('page_id', '?')}")
    print(f"  {BOLD}Project{RESET}: {pg.get('item_id', '?')}")
    print(f"  {BOLD}Author{RESET}: {pg.get('author', 'N/A')}")
    draft_label = f"{YELLOW}draft{RESET}" if pg.get("is_draft") else f"{GREEN}published{RESET}"
    print(f"  {BOLD}Status{RESET}: {draft_label}")
    print(f"  {BOLD}Created{RESET}: {pg.get('addtime', 'N/A')}")
    print()
    content = pg.get("content", "")
    if content:
        print(content[:4000])
        if len(content) > 4000:
            print(f"\n  ... ({len(content)} chars total, truncated)")
    else:
        print("  (empty page)")


def cmd_goto(args):
    if args.page_id:
        from tool.SHOWDOC.logic.chrome.api import navigate_to_page
        print(f"  {BOLD}{BLUE}Navigating{RESET} to page {args.page_id}...", flush=True)
        result = navigate_to_page(args.item_id, args.page_id, args.port)
    else:
        from tool.SHOWDOC.logic.chrome.api import navigate_to_project
        print(f"  {BOLD}{BLUE}Navigating{RESET} to project {args.item_id}...", flush=True)
        result = navigate_to_project(args.item_id, args.port)

    if result.get("ok"):
        print(f"  {BOLD}URL{RESET}: {result.get('url', 'N/A')}")
        if result.get("title"):
            print(f"  {BOLD}Title{RESET}: {result['title']}")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Navigation failed')}")


def cmd_home(args):
    from tool.SHOWDOC.logic.chrome.api import navigate_home
    print(f"  {BOLD}{BLUE}Navigating{RESET} to dashboard...", flush=True)
    result = navigate_home(args.port)
    if result.get("ok"):
        print(f"  {BOLD}URL{RESET}: {result.get('url', 'N/A')}")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Navigation failed')}")


def cmd_screenshot(args):
    from tool.SHOWDOC.logic.chrome.api import take_screenshot
    output = args.output
    result = take_screenshot(args.port, output)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Saved{RESET} screenshot to {result['path']}.", flush=True)
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Screenshot failed')}")


def cmd_search(args):
    from tool.SHOWDOC.logic.chrome.api import search_project
    result = search_project(args.item_id, args.keyword, args.port)
    if result.get("error"):
        print(f"  {BOLD}{RED}Error{RESET}: {result['error']}")
        return

    results = result.get("results", [])
    project_name = result.get("item_name", args.item_id)
    if not results:
        print(f"  No results for '{args.keyword}' in {project_name}.")
        return

    print(f"  {BOLD}Search{RESET}: '{args.keyword}' in {project_name} ({len(results)} results):")
    for r in results:
        print(f"    [{r['page_id']}] {r['title']}")
        if r.get("snippet"):
            snippet = r["snippet"].replace("\n", " ").strip()
            print(f"        {snippet[:120]}...")


def cmd_save_page(args):
    from tool.SHOWDOC.logic.chrome.api import save_page
    content = args.content
    if args.file:
        with open(args.file, "r") as f:
            content = f.read()
    if not content:
        print(f"  {BOLD}{RED}Error{RESET}: provide --content or --file.")
        return

    action = "Updating" if args.page_id else "Creating"
    print(f"  {BOLD}{BLUE}{action}{RESET} page '{args.title}'...", flush=True)
    result = save_page(args.item_id, args.title, content,
                       cat_id=args.cat_id, page_id=args.page_id, port=args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} {result.get('action', 'saved')} page (ID: {result.get('page_id', '?')}).")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Save failed')}")


def cmd_delete_page(args):
    from tool.SHOWDOC.logic.chrome.api import delete_page
    print(f"  {BOLD}{BLUE}Deleting{RESET} page {args.page_id}...", flush=True)
    result = delete_page(args.page_id, args.item_id, args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} deleted page {args.page_id}.")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Delete failed')}")


def cmd_create_project(args):
    from tool.SHOWDOC.logic.chrome.api import create_project
    print(f"  {BOLD}{BLUE}Creating{RESET} project '{args.name}'...", flush=True)
    result = create_project(args.name, item_type=args.type, description=args.description,
                            password=args.password, port=args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} created project (ID: {result.get('item_id', '?')}).")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Create failed')}")


def cmd_create_catalog(args):
    from tool.SHOWDOC.logic.chrome.api import create_catalog
    print(f"  {BOLD}{BLUE}Creating{RESET} catalog '{args.name}'...", flush=True)
    result = create_catalog(args.item_id, args.name, parent_cat_id=args.parent, port=args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} created catalog (ID: {result.get('cat_id', '?')}).")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Create failed')}")


def cmd_delete_catalog(args):
    from tool.SHOWDOC.logic.chrome.api import delete_catalog
    print(f"  {BOLD}{BLUE}Deleting{RESET} catalog {args.cat_id}...", flush=True)
    result = delete_catalog(args.cat_id, args.item_id, args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} deleted catalog {args.cat_id}.")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Delete failed')}")


def cmd_star(args):
    from tool.SHOWDOC.logic.chrome.api import star_project, unstar_project
    if args.action == "star":
        result = star_project(args.item_id, args.port)
    else:
        result = unstar_project(args.item_id, args.port)
    if result.get("ok"):
        print(f"  {BOLD}{GREEN}Successfully{RESET} {'starred' if args.action == 'star' else 'unstarred'} project {args.item_id}.")
    else:
        print(f"  {BOLD}{RED}Error{RESET}: {result.get('error', 'Failed')}")


def main():
    tool = ToolBase("SHOWDOC")

    parser = argparse.ArgumentParser(
        description="SHOWDOC - ShowDoc documentation platform via CDMCP",
        add_help=False,
    )
    parser.add_argument("--port", type=int, default=9222, help="Chrome CDP port")

    sub = parser.add_subparsers(dest="command")

    # Session
    sub.add_parser("boot", help="Boot CDMCP session")
    sub.add_parser("status", help="Check session and auth")

    # Read
    sub.add_parser("user", help="Show user profile")
    sub.add_parser("projects", help="List projects")
    sub.add_parser("home", help="Navigate to dashboard")

    p_proj = sub.add_parser("project", help="Show project info")
    p_proj.add_argument("item_id", help="Project/item ID")

    p_cat = sub.add_parser("catalog", help="Show project catalogs")
    p_cat.add_argument("item_id", help="Project/item ID")

    p_pg = sub.add_parser("page", help="Show page content")
    p_pg.add_argument("page_id", help="Page ID")

    p_search = sub.add_parser("search", help="Search within a project")
    p_search.add_argument("item_id", help="Project/item ID")
    p_search.add_argument("keyword", help="Search keyword")

    # Write: pages
    p_sp = sub.add_parser("save-page", help="Create or update a page")
    p_sp.add_argument("item_id", help="Project/item ID")
    p_sp.add_argument("title", help="Page title")
    p_sp.add_argument("--content", default="", help="Page content (markdown)")
    p_sp.add_argument("--file", default="", help="Read content from file")
    p_sp.add_argument("--cat-id", dest="cat_id", default="0", help="Catalog ID (default: root)")
    p_sp.add_argument("--page-id", dest="page_id", default=None, help="Page ID (for update)")

    p_dp = sub.add_parser("delete-page", help="Delete a page")
    p_dp.add_argument("page_id", help="Page ID")
    p_dp.add_argument("item_id", help="Project/item ID")

    # Write: projects
    p_cp = sub.add_parser("create-project", help="Create a new project")
    p_cp.add_argument("name", help="Project name")
    p_cp.add_argument("--type", default="1", choices=["1", "4", "5"],
                      help="Type: 1=Regular, 4=Table, 5=Whiteboard")
    p_cp.add_argument("--description", default="", help="Project description")
    p_cp.add_argument("--password", default="", help="Access password (makes private)")

    p_star = sub.add_parser("star", help="Star a project")
    p_star.add_argument("item_id", help="Project/item ID")
    p_star.set_defaults(action="star")

    p_unstar = sub.add_parser("unstar", help="Unstar a project")
    p_unstar.add_argument("item_id", help="Project/item ID")
    p_unstar.set_defaults(action="unstar")

    # Write: catalogs
    p_cc = sub.add_parser("create-catalog", help="Create a new catalog folder")
    p_cc.add_argument("item_id", help="Project/item ID")
    p_cc.add_argument("name", help="Catalog name")
    p_cc.add_argument("--parent", default="0", help="Parent catalog ID (default: root)")

    p_dc = sub.add_parser("delete-catalog", help="Delete a catalog folder")
    p_dc.add_argument("cat_id", help="Catalog ID")
    p_dc.add_argument("item_id", help="Project/item ID")

    # Navigation
    p_goto = sub.add_parser("goto", help="Navigate to project or page")
    p_goto.add_argument("item_id", help="Project/item ID")
    p_goto.add_argument("page_id", nargs="?", default=None, help="Page ID (optional)")

    p_ss = sub.add_parser("screenshot", help="Take screenshot")
    p_ss.add_argument("--output", default="/tmp/showdoc_screenshot.png")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()

    commands = {
        "boot": cmd_boot,
        "status": cmd_status,
        "user": cmd_user,
        "projects": cmd_projects,
        "project": cmd_project,
        "catalog": cmd_catalog,
        "page": cmd_page,
        "search": cmd_search,
        "save-page": cmd_save_page,
        "delete-page": cmd_delete_page,
        "create-project": cmd_create_project,
        "create-catalog": cmd_create_catalog,
        "delete-catalog": cmd_delete_catalog,
        "star": cmd_star,
        "unstar": cmd_star,
        "goto": cmd_goto,
        "home": cmd_home,
        "screenshot": cmd_screenshot,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        print(f"  {BOLD}SHOWDOC{RESET} - ShowDoc documentation platform via CDMCP.")
        print()
        print(f"  {BOLD}Session{RESET}:")
        print(f"    boot                           Boot CDMCP session")
        print(f"    status                         Check session and auth state")
        print()
        print(f"  {BOLD}Read{RESET}:")
        print(f"    user                           Show user profile")
        print(f"    projects                       List all projects")
        print(f"    project <item_id>              Show project info and doc tree")
        print(f"    catalog <item_id>              Show catalog folders")
        print(f"    page <page_id>                 Show page content")
        print(f"    search <item_id> <keyword>     Full-text search in project")
        print()
        print(f"  {BOLD}Write{RESET}:")
        print(f"    save-page <item_id> <title>    Create/update page (--content/--file)")
        print(f"    delete-page <page_id> <item>   Delete a page")
        print(f"    create-project <name>          Create a new project")
        print(f"    create-catalog <item_id> <n>   Create a catalog folder")
        print(f"    delete-catalog <cat_id> <item> Delete a catalog folder")
        print(f"    star/unstar <item_id>          Star or unstar a project")
        print()
        print(f"  {BOLD}Navigation{RESET}:")
        print(f"    goto <item_id> [page_id]       Navigate browser to project/page")
        print(f"    home                           Navigate to dashboard")
        print(f"    screenshot [--output]          Take screenshot")
        print()
        print(f"  {BOLD}Options{RESET}:")
        print(f"    --port N                       Chrome CDP port (default: 9222)")


if __name__ == "__main__":
    main()
