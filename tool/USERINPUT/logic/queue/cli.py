"""USERINPUT --queue — Queue management subcommand.

Handles: --queue --list, --queue --add, --queue --delete,
         --queue --gui, --queue --move-*, --queue (interactive).
"""
import os
import sys
import tempfile
from pathlib import Path

from tool.USERINPUT.logic import (
    TOOL_INTERNAL, get_config, get_msg,
    UserInputFatalError, UserInputRetryableError,
)
from tool.USERINPUT.logic.queue import store as qstore


def run_queue(tool, args, unknown=None):
    """Dispatch queue subcommands. Called from main.py when --queue is set."""
    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    has_reorder = any(v is not None for v in [
        args.move_up, args.move_down, args.move_to_top, args.move_to_bottom
    ])
    queue_label = get_msg("label_queue", "Queue")

    if args.list:
        prompts = qstore.list_all()
        if not prompts:
            print(f"{BOLD}{queue_label}{RESET}: {get_msg('label_queue_empty', 'empty.')}")
            return 0
        n = len(prompts)
        unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
        print(f"{BOLD}{queue_label}{RESET} ({n} {unit}):")
        for i, p in enumerate(prompts):
            flat = p.replace("\n", " ").replace("\r", " ")
            display = flat if len(flat) <= 80 else flat[:77] + "..."
            print(f"  {i}: {display}")
        print(f"\n{get_msg('label_queue_hint', 'Manage: --queue --add <text> | --delete <id> | --move-up/down/to-top/to-bottom <id> | --gui')}")
        return 0

    if args.gui:
        return _queue_gui(tool)

    if args.add:
        qstore.add(args.add)
        print(f"{BOLD}{GREEN}{get_msg('label_successfully_added', 'Successfully added')}{RESET} {get_msg('label_to_queue', 'to queue')}.")
        return 0

    if args.delete is not None:
        if qstore.remove(args.delete):
            print(f"{BOLD}{GREEN}{get_msg('label_successfully_deleted', 'Successfully deleted')}{RESET} {get_msg('label_queue_item', 'queue item')} {args.delete}.")
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_delete', 'Failed to delete')}{RESET} {get_msg('label_queue_item', 'queue item')} {args.delete}.", file=sys.stderr)
            return 1
        return 0

    if has_reorder:
        ops = [
            (args.move_up, qstore.move_up, get_msg("label_moved_up", "Moved up")),
            (args.move_down, qstore.move_down, get_msg("label_moved_down", "Moved down")),
            (args.move_to_top, qstore.move_to_top, get_msg("label_moved_to_top", "Moved to top")),
            (args.move_to_bottom, qstore.move_to_bottom, get_msg("label_moved_to_bottom", "Moved to bottom")),
        ]
        for val, func, label in ops:
            if val is not None:
                if func(val):
                    print(f"{BOLD}{GREEN}{label}{RESET} {get_msg('label_queue_item', 'item')} {val}.")
                else:
                    print(f"{BOLD}{RED}{get_msg('label_failed_to_move', 'Failed to move')}{RESET} {get_msg('label_queue_item', 'item')} {val}.", file=sys.stderr)
                    return 1
        return 0

    return _queue_add_interactive(tool, args)


def _queue_add_interactive(tool, args):
    """Open USERINPUT GUI and save the result to the queue."""
    from interface.config import get_color
    BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
    RED = get_color("RED")

    from tool.USERINPUT.logic import get_cursor_session_title
    from tool.USERINPUT.logic.cli import get_user_input_tkinter

    try:
        result = get_user_input_tkinter(
            title=get_cursor_session_title(args.id) + " [Queue]",
            timeout=args.timeout,
            hint_text=args.hint,
            custom_id=args.id,
        )
    except UserInputFatalError as e:
        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        print(f"{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
        return 130
    except (UserInputRetryableError, RuntimeError) as e:
        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        print(f"{RED}Error{RESET}: {e}", file=sys.stderr)
        return 1

    if result and result.strip():
        text = result.strip()
        if text.startswith("__PARTIAL_TIMEOUT__:"):
            text = text[len("__PARTIAL_TIMEOUT__:"):]
        if text:
            qstore.add(text)
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_to_queue', 'to queue')}.")
            return 0

    sys.stdout.write("\r\033[K"); sys.stdout.flush()
    print(f"{BOLD}{get_msg('label_queue', 'Queue')}{RESET}: {get_msg('label_queue_nothing_to_save', 'nothing to save (empty input).')}")
    return 1


def _queue_gui(tool):
    """Open the editable list GUI for queue management."""
    python_exe = tool.get_python_exe()
    items = qstore.list_all()

    gui_script = r'''
import os, sys, json, traceback
from pathlib import Path

project_root = %(project_root)r
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interface.gui import setup_gui_environment, EditableListWindow
setup_gui_environment()

items = %(items)r

win = EditableListWindow(
    title="USERINPUT Queue Manager",
    internal_dir=%(internal_dir)r,
    tool_name="USERINPUT",
    items=items,
    list_label="Queued prompts (drag to reorder):",
    save_text="Save",
    cancel_text="Cancel",
    window_size="650x450",
    allow_add=True,
    allow_edit=True,
    allow_delete=True,
)
win.run()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'items': items,
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_queue_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(gui_script)
        tmp_path = tmp.name

    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, 600, None)
        from interface.config import get_color
        BOLD = get_color("BOLD")
        GREEN = get_color("GREEN")
        RED = get_color("RED")
        RESET = get_color("RESET")

        if res.get("status") == "success":
            new_items = res.get("data", [])
            if isinstance(new_items, list):
                qstore.replace_all(new_items)
                n = len(new_items)
                unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
                print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_queue', 'queue')} ({n} {unit}).")
            return 0
        elif res.get("status") == "cancelled":
            print(f"{BOLD}{get_msg('label_cancelled_queue_editor', 'Cancelled queue editor.')}{RESET}")
            return 0
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_save', 'Failed to save')}{RESET} {get_msg('label_queue', 'queue')}.", file=sys.stderr)
            return 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
