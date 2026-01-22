import os
import sys
import json
import argparse
import subprocess
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any

def handle_gui_remote_command(tool_name: str, project_root: Path, command: str, unknown_args: List[str], translation_helper: callable) -> int:
    """
    Unified handler for remote GUI commands (stop, submit, cancel, add_time).
    """
    from logic.config import get_color
    BOLD, RED, YELLOW, RESET = get_color("BOLD", "\033[1m"), get_color("RED", "\033[31m"), get_color("YELLOW", "\033[33m"), get_color("RESET", "\033[0m")
    
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--id", type=str)
    args, unknown = parser.parse_known_args(unknown_args)
    
    target_pid = None
    if unknown:
        try: target_pid = int(unknown[0])
        except: pass

    target_id = args.id

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
                    registered_id = info.get("custom_id")
                    if pid is None: continue
                    
                    # Match criteria
                    match = False
                    if target_pid is not None:
                        if pid == target_pid: match = True
                    elif target_id is not None:
                        if registered_id == target_id: match = True
                    elif registered_tool == tool_name:
                        match = True
                    
                    if match:
                        # Create the appropriate flag file
                        flag_file = stop_dir / f"{pid}.{command}"
                        flag_file.touch()
                        found += 1
            except: continue
    
    if found > 0:
        if command == "stop":
            template = translation_helper('instances_stopped', 'Stopped {count} GUI instances.')
            msg = template.format(count=found)
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

def run_gui_subprocess(tool_instance, python_exe: str, script_path: str, timeout: int, custom_id: str = None) -> Dict[str, Any]:
    """
    Unified launcher for GUI subprocesses with signal redirection and result capture.
    Used by parent processes (e.g. tool/NAME/main.py).
    """
    from logic.config import get_color
    BOLD, BLUE, RESET = get_color("BOLD", "\033[1m"), get_color("BLUE", "\033[34m"), get_color("RESET", "\033[0m")
    
    # 1. Start subprocess in new session to decouple from parent's process group
    proc = subprocess.Popen([python_exe, script_path], 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            text=True, encoding='utf-8', start_new_session=True)
    
    # Display PID for precise termination if needed
    tool_name = tool_instance.tool_name
    label_waiting_key = "label_waiting_gui"
    if tool_name == "FILEDIALOG": label_waiting_key = "label_waiting_selection"
    
    label_waiting = tool_instance.get_translation(label_waiting_key, f"Waiting for {tool_name} feedback via GUI")
    sys.stdout.write(f"\r\033[K{BOLD}{BLUE}{label_waiting}{RESET} (PID: {proc.pid})...")
    sys.stdout.flush()

    stderr_content = []
    def read_stderr():
        for line in iter(proc.stderr.readline, ''): stderr_content.append(line)
        proc.stderr.close()
    t_stderr = threading.Thread(target=read_stderr, daemon=True)
    t_stderr.start()

    parent_timeout = timeout + 300
    start_wait = time.time()
    
    stdout = ""
    is_interrupted = False
    try:
        while proc.poll() is None:
            if time.time() - start_wait > parent_timeout:
                proc.kill()
                sys.stdout.write("\r\033[K"); sys.stdout.flush()
                return {"status": "timeout", "data": None}
            time.sleep(0.5)
        stdout, _ = proc.communicate()
        t_stderr.join(timeout=2)
    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, KeyboardInterrupt):
            is_interrupted = True
        
        # Graceful stop via flag file
        stops_dir = tool_instance.project_root / "data" / "run" / "stops"
        stops_dir.mkdir(parents=True, exist_ok=True)
        stop_file = stops_dir / f"{proc.pid}.stop"
        stop_file.touch()
        
        try:
            # Wait for GUI to detect flag, finalize and print JSON
            stdout, _ = proc.communicate(timeout=4)
            t_stderr.join(timeout=1)
        except:
            proc.kill()
            stdout = ""
        
        if not stdout:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            if is_interrupted:
                return {"status": "terminated", "data": None, "reason": "interrupted"}
            raise e

    sys.stdout.write("\r\033[K"); sys.stdout.flush()
    stderr = "".join(stderr_content)
    
    # Parse JSON result
    res = None
    for line in stdout.splitlines():
        if line.startswith("GDS_GUI_RESULT_JSON:"):
            try:
                res = json.loads(line[len("GDS_GUI_RESULT_JSON:"):])
                break
            except: pass
    
    if res:
        # If it was terminated, refine reason
        if res.get("status") == "terminated":
            if is_interrupted:
                res["reason"] = "interrupted"
            elif not res.get("reason"):
                res["reason"] = "stop" # Default for termination via flag
        return res
    
    # Error fallback for crashes
    if proc.returncode != 0:
        sig_codes = [-15, -2, -9, -11, -6, 15, 2, 9, 11, 6, 143, 130, 137, 139, 134]
        if proc.returncode in sig_codes:
            return {"status": "terminated", "data": None, "reason": "signal"}
            
    return {"status": "error", "message": stderr or "No valid response from GUI"}

def handle_gui_stop_command(tool_name: str, project_root: Path, unknown_args: List[str], translation_helper: callable) -> int:
    return handle_gui_remote_command(tool_name, project_root, "stop", unknown_args, translation_helper)
