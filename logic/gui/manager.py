import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional

def handle_gui_remote_command(tool_name: str, project_root: Path, command: str, unknown_args: List[str], translation_helper: callable) -> int:
    """
    Unified handler for remote GUI commands (stop, submit, cancel, add_time).
    """
    from logic.config import get_color
    BOLD, RED, YELLOW, RESET = get_color("BOLD", "\033[1m"), get_color("RED", "\033[31m"), get_color("YELLOW", "\033[33m"), get_color("RESET", "\033[0m")
    
    target_pid = None
    if unknown_args:
        try: target_pid = int(unknown_args[0])
        except: pass

    instance_dir = project_root / "data" / "run" / "instances"
    stop_dir = project_root / "data" / "run" / "stops"
    stop_dir.mkdir(parents=True, exist_ok=True)

    found = 0
    if instance_dir.exists():
        for f in instance_dir.glob("gui_*.json"):
            try:
                with open(f, "r") as info_file:
                    info = json.load(info_file)
                    pid = info.get("pid")
                    registered_tool = info.get("tool_name")
                    if pid is None: continue
                    
                    # Check if this PID/tool should be stopped
                    if target_pid is not None:
                        if pid != target_pid: continue
                    elif registered_tool != tool_name:
                        continue
                    
                    # Create the appropriate flag file
                    flag_file = stop_dir / f"{pid}.{command}"
                    flag_file.touch()
                    found += 1
            except: continue
    
    if found > 0:
        if command == "stop":
            msg = translation_helper('instances_stopped', 'Stopped {count} GUI instances.', count=found)
            label = translation_helper('label_terminated', 'Terminated')
            print(f"{BOLD}{RED}{label}{RESET}: {msg}")
        else:
            # Simple success message for other commands
            print(f"{BOLD}{YELLOW}Info{RESET}: Sent '{command}' to {found} {tool_name} instances.")
    else:
        if target_pid:
            print(f"{BOLD}{YELLOW}Warning{RESET}: PID {target_pid} not found in active {tool_name} instances.")
        else:
            msg = translation_helper('no_instances_found', f'No active {tool_name} GUI instances found.')
            print(msg)
    return 0

def handle_gui_stop_command(tool_name: str, project_root: Path, unknown_args: List[str], translation_helper: callable) -> int:
    return handle_gui_remote_command(tool_name, project_root, "stop", unknown_args, translation_helper)

