#!/usr/bin/env python3
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

from logic.tool.blueprint.base import ToolBase
from interface.config import get_color


def main():
    tool = ToolBase("ASANA")

    parser = argparse.ArgumentParser(
        description="Asana project management via Chrome CDP",
        epilog="MCP commands use --mcp- prefix: e.g., ASANA --mcp-status, ASANA --mcp-page",
        add_help=False,
    )
    sub = parser.add_subparsers(dest="command", help="MCP subcommand (use --mcp-<cmd> prefix)")

    sub.add_parser("me", help="Show authenticated user info")
    sub.add_parser("workspaces", help="List workspaces")

    proj_p = sub.add_parser("projects", help="List projects in a workspace")
    proj_p.add_argument("workspace_gid", help="Workspace GID")
    proj_p.add_argument("--limit", type=int, default=20)

    task_p = sub.add_parser("tasks", help="List tasks assigned to me")
    task_p.add_argument("workspace_gid", help="Workspace GID")
    task_p.add_argument("--limit", type=int, default=20)

    ct_p = sub.add_parser("create-task", help="Create a new task")
    ct_p.add_argument("workspace_gid", help="Workspace GID")
    ct_p.add_argument("name", help="Task name")
    ct_p.add_argument("--notes", default="", help="Task description")
    ct_p.add_argument("--due", default=None, help="Due date (YYYY-MM-DD)")
    ct_p.add_argument("--project", default=None, help="Project GID")

    cp_p = sub.add_parser("create-project", help="Create a new project")
    cp_p.add_argument("workspace_gid", help="Workspace GID")
    cp_p.add_argument("name", help="Project name")
    cp_p.add_argument("--notes", default="", help="Project description")

    search_p = sub.add_parser("search", help="Search tasks")
    search_p.add_argument("workspace_gid", help="Workspace GID")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=10)

    done_p = sub.add_parser("complete", help="Mark a task as completed")
    done_p.add_argument("task_gid", help="Task GID")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    from tool.ASANA.logic.chrome.api import (
        get_me, list_workspaces, list_projects, list_tasks,
        create_task, create_project, complete_task, search_tasks,
    )

    def _err(data):
        errors = data.get("errors", [])
        return errors[0].get("message", "Unknown error") if errors else "Unknown error"

    if args.command == "me":
        r = get_me()
        d = r.get("data", {})
        if d:
            print(f"  Name:  {d.get('name', '?')}")
            print(f"  Email: {d.get('email', '?')}")
            print(f"  GID:   {d.get('gid', '?')}")
            for ws in d.get("workspaces", []):
                print(f"  Workspace: {ws.get('name')} ({ws.get('gid')})")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "workspaces":
        r = list_workspaces()
        ws_list = r.get("data", [])
        if isinstance(ws_list, list):
            if not ws_list:
                print("  (no workspaces)")
            for ws in ws_list:
                print(f"  {ws.get('name', '?'):<40} GID: {ws.get('gid', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "projects":
        r = list_projects(args.workspace_gid, limit=args.limit)
        projects = r.get("data", [])
        if isinstance(projects, list):
            if not projects:
                print("  (no projects)")
            for p in projects:
                owner = p.get("owner", {})
                print(f"  {p.get('name', '?'):<40} owner: {owner.get('name', '?') if owner else '?'}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "tasks":
        r = list_tasks(args.workspace_gid, limit=args.limit)
        tasks = r.get("data", [])
        if isinstance(tasks, list):
            if not tasks:
                print("  (no tasks)")
            for t in tasks:
                done = "x" if t.get("completed") else " "
                due = t.get("due_on", "")
                print(f"  [{done}] {t.get('name', '?'):<50} due: {due or '-'}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "create-task":
        r = create_task(args.workspace_gid, args.name,
                        notes=args.notes, due_on=args.due,
                        project_gid=args.project)
        d = r.get("data", {})
        if d and d.get("gid"):
            print(f"{BOLD}{GREEN}Created{RESET}: {d.get('name')} (GID: {d.get('gid')})")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "create-project":
        r = create_project(args.workspace_gid, args.name, notes=args.notes)
        d = r.get("data", {})
        if d and d.get("gid"):
            print(f"{BOLD}{GREEN}Created{RESET}: {d.get('name')} (GID: {d.get('gid')})")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "search":
        r = search_tasks(args.workspace_gid, args.query, limit=args.limit)
        tasks = r.get("data", [])
        if isinstance(tasks, list):
            if not tasks:
                print("  (no results)")
            for t in tasks:
                done = "x" if t.get("completed") else " "
                print(f"  [{done}] {t.get('name', '?'):<50} GID: {t.get('gid', '?')}")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    elif args.command == "complete":
        r = complete_task(args.task_gid)
        d = r.get("data", {})
        if d and d.get("completed"):
            print(f"{BOLD}{GREEN}Completed{RESET}: {d.get('name')} (GID: {args.task_gid})")
        else:
            print(f"{BOLD}{RED}Error{RESET}: {_err(r)}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
