"""USERINPUT --system-prompt — System prompt management subcommand.

Handles: --system-prompt --list, --system-prompt --add, --system-prompt --delete,
         --system-prompt --gui, --system-prompt --move-*.
"""
import os
import sys
import json
import tempfile

from tool.USERINPUT.logic import (
    TOOL_INTERNAL, get_config, save_config, get_msg, reorder_list,
)


def run_prompt(tool, args, unknown=None):
    """Dispatch system-prompt subcommands. Called from main.py."""
    config = get_config()
    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    RESET = get_color("RESET")

    prompts = config.get("system_prompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]

    sp_label = get_msg("label_system_prompts", "System prompts")

    if args.list:
        if not prompts:
            print(f"{BOLD}{sp_label}{RESET}: {get_msg('label_system_prompts_empty', 'empty.')}")
        else:
            n = len(prompts)
            unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
            print(f"{BOLD}{sp_label}{RESET} ({n} {unit}):")
            for i, p in enumerate(prompts):
                flat = p.replace("\n", " ").replace("\r", " ")
                display = flat if len(flat) <= 80 else flat[:77] + "..."
                print(f"  {i}: {display}")
            print(f"\n{get_msg('label_sp_hint', 'Manage: --system-prompt --add <text> | --delete <id> | --move-up/down/to-top/to-bottom <id> | --gui')}")
        return 0

    if args.gui:
        return _prompt_gui(tool, config)

    has_reorder = any(v is not None for v in [
        args.move_up, args.move_down, args.move_to_top, args.move_to_bottom
    ])
    if has_reorder:
        label_map = {
            "up": get_msg("label_moved_up", "Moved up"),
            "down": get_msg("label_moved_down", "Moved down"),
            "top": get_msg("label_moved_to_top", "Moved to top"),
            "bottom": get_msg("label_moved_to_bottom", "Moved to bottom"),
        }
        ops = [
            (args.move_up, "up"), (args.move_down, "down"),
            (args.move_to_top, "top"), (args.move_to_bottom, "bottom"),
        ]
        sp_item = get_msg("label_system_prompt_item", "system prompt")
        for val, direction in ops:
            if val is not None:
                if reorder_list(prompts, val, direction):
                    config["system_prompt"] = prompts
                    save_config(config)
                    print(f"{BOLD}{GREEN}{label_map[direction]}{RESET} {sp_item} {val}.")
                else:
                    print(f"{BOLD}{RED}{get_msg('label_failed_to_move', 'Failed to move')}{RESET} {sp_item} {val}.", file=sys.stderr)
                    return 1
        return 0

    if args.add:
        prompts.append(args.add)
        config["system_prompt"] = prompts
        save_config(config)
        n = len(prompts)
        unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
        print(f"{BOLD}{GREEN}{get_msg('label_successfully_added', 'Successfully added')}{RESET} {sp_label} ({n} {unit}).")
        return 0

    if args.delete is not None:
        idx = args.delete
        if 0 <= idx < len(prompts):
            prompts.pop(idx)
            config["system_prompt"] = prompts
            save_config(config)
            n = len(prompts)
            rem_label = get_msg("label_remaining", "remaining")
            print(f"{BOLD}{GREEN}{get_msg('label_successfully_deleted', 'Successfully deleted')}{RESET} {sp_label} {idx} ({n} {rem_label}).")
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_delete', 'Failed to delete')}{RESET} {sp_label} {idx}.", file=sys.stderr)
            return 1
        return 0

    print("Usage: USERINPUT --system-prompt --add <str> | --delete <id> | --list | --gui")
    print("  Reorder: --move-up <id> | --move-down <id> | --move-to-top <id> | --move-to-bottom <id>")
    return 1


def _prompt_gui(tool, config):
    """Open the editable list GUI for system prompt management."""
    prompts = config.get("system_prompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]

    python_exe = tool.get_python_exe()

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
    title="USERINPUT System Prompts",
    internal_dir=%(internal_dir)r,
    tool_name="USERINPUT",
    items=items,
    list_label="System prompts:",
    save_text="Save",
    cancel_text="Cancel",
    window_size="700x500",
    allow_add=True,
    allow_edit=True,
    allow_delete=True,
)
win.run()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'items': prompts,
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_prompt_gui_', suffix='.py', delete=False) as tmp:
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
            new_prompts = res.get("data", [])
            if isinstance(new_prompts, list):
                config["system_prompt"] = new_prompts
                save_config(config)
                n = len(new_prompts)
                unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
                print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_system_prompts', 'system prompts')} ({n} {unit}).")
            return 0
        elif res.get("status") == "cancelled":
            print(f"{BOLD}{get_msg('label_cancelled_prompt_editor', 'Cancelled system prompt editor.')}{RESET}")
            return 0
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_save', 'Failed to save')}{RESET} {get_msg('label_system_prompts', 'system prompts')}.", file=sys.stderr)
            return 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
