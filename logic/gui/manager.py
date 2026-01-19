import os
import sys
import json
import argparse
from pathlib import Path
from typing import List, Optional

def handle_gui_stop_command(tool_name: str, project_root: Path, unknown_args: List[str], translation_helper: callable) -> int:
    """
    Unified handler for the 'stop' command across all GUI tools.
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
                    # For specific tools, we could filter by info.get("class")
                    # but usually 'stop' should affect the tool it's called from.
                    pid = info.get("pid")
                    if not pid: continue
                    if target_pid and pid != target_pid: continue
                    
                    # Create stop flag
                    (stop_dir / f"{pid}.stop").touch()
                    found += 1
            except: continue
    
    if found > 0:
        msg = translation_helper('instances_stopped', 'Stopped {count} GUI instances.', count=found)
        label = translation_helper('label_terminated', 'Terminated')
        print(f"{BOLD}{RED}{label}{RESET}: {msg}")
    else:
        if target_pid:
            print(f"{BOLD}{YELLOW}Warning{RESET}: PID {target_pid} not found in active instances.")
        else:
            msg = translation_helper('no_instances_found', 'No active GUI instances found.')
            print(msg)
    return 0

