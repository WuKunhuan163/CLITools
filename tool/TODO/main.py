#!/usr/bin/env python3
"""TODO — Agent task management tool.

Provides a persistent, JSON-backed todo list for agents to track
in-progress work, pending tasks, and completed items.

Usage:
    TODO add "Implement feature X"
    TODO list [--status pending|in_progress|completed|abandoned]
    TODO done <id>
    TODO start <id>
    TODO abandon <id>
    TODO remove <id>
    TODO clear [--done]
"""
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
from logic.config import get_color
from logic.turing.status import fmt_status, fmt_detail, fmt_warning


def _format_item(item, bold, dim, reset, green, red, yellow, cyan):
    status = item["status"]
    sid = item["id"]
    content = item["content"]

    status_colors = {
        "pending": dim,
        "in_progress": cyan,
        "completed": green,
        "abandoned": red,
    }
    status_labels = {
        "pending": "pending",
        "in_progress": "active",
        "completed": "done",
        "abandoned": "abandoned",
    }
    color = status_colors.get(status, "")
    label = status_labels.get(status, status)
    return f"  {dim}{sid}{reset}  {color}{bold}{label}{reset}  {content}"


def main():
    tool = ToolBase("TODO")

    parser = argparse.ArgumentParser(
        description="Agent task management", add_help=False)
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a new todo item")
    add_p.add_argument("content", nargs="+", help="Task description")
    add_p.add_argument("--context", default="default", help="Todo list context")

    list_p = sub.add_parser("list", help="List todo items")
    list_p.add_argument("--status", help="Filter by status")
    list_p.add_argument("--context", default="default", help="Todo list context")

    done_p = sub.add_parser("done", help="Mark item as completed")
    done_p.add_argument("id", help="Item ID")
    done_p.add_argument("--context", default="default")

    start_p = sub.add_parser("start", help="Mark item as in-progress")
    start_p.add_argument("id", help="Item ID")
    start_p.add_argument("--context", default="default")

    abandon_p = sub.add_parser("abandon", help="Mark item as abandoned")
    abandon_p.add_argument("id", help="Item ID")
    abandon_p.add_argument("--context", default="default")

    rm_p = sub.add_parser("remove", help="Remove item permanently")
    rm_p.add_argument("id", help="Item ID")
    rm_p.add_argument("--context", default="default")

    clear_p = sub.add_parser("clear", help="Clear todo items")
    clear_p.add_argument("--done", action="store_true", help="Only clear completed/abandoned")
    clear_p.add_argument("--context", default="default")

    if tool.handle_command_line(parser):
        return

    args = parser.parse_args()

    BOLD = get_color("BOLD", "\033[1m")
    DIM = get_color("DIM", "\033[2m")
    GREEN = get_color("GREEN_NORMAL", "\033[32m")
    RED = get_color("RED_NORMAL", "\033[31m")
    YELLOW = get_color("YELLOW_NORMAL", "\033[33m")
    CYAN = get_color("CYAN", "\033[36m")
    RESET = get_color("RESET", "\033[0m")

    from tool.TODO.logic.store import (
        add as store_add, update_status, remove, list_items, clear,
    )

    if args.command == "add":
        content = " ".join(args.content)
        item = store_add(content, context=args.context)
        print(fmt_status("Added.", complement=f"[{item['id']}] {content}", indent=0))

    elif args.command == "list":
        items = list_items(context=args.context, status_filter=args.status)
        if not items:
            print(fmt_detail("No todo items.", indent=0))
            return
        for item in items:
            print(_format_item(item, BOLD, DIM, RESET, GREEN, RED, YELLOW, CYAN))

    elif args.command == "done":
        result = update_status(args.id, "completed", context=args.context)
        if result:
            print(fmt_status("Completed.", complement=f"[{args.id}]", style="success", indent=0))
        else:
            print(fmt_warning(f"Item {args.id} not found.", indent=0))

    elif args.command == "start":
        result = update_status(args.id, "in_progress", context=args.context)
        if result:
            print(fmt_status("Started.", complement=f"[{args.id}]", indent=0))
        else:
            print(fmt_warning(f"Item {args.id} not found.", indent=0))

    elif args.command == "abandon":
        result = update_status(args.id, "abandoned", context=args.context)
        if result:
            print(fmt_status("Abandoned.", complement=f"[{args.id}]", indent=0))
        else:
            print(fmt_warning(f"Item {args.id} not found.", indent=0))

    elif args.command == "remove":
        if remove(args.id, context=args.context):
            print(fmt_status("Removed.", complement=f"[{args.id}]", indent=0))
        else:
            print(fmt_warning(f"Item {args.id} not found.", indent=0))

    elif args.command == "clear":
        count = clear(context=args.context, only_done=args.done)
        label = "Cleared completed." if args.done else "Cleared all."
        print(fmt_status(label, complement=f"{count} items removed.", indent=0))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
