import os
import sys
import json
import argparse
import subprocess
import time
import threading
from pathlib import Path
import random
import hashlib
from typing import List, Optional, Dict, Any, Callable

def handle_gui_remote_command(tool_name: str, project_root: Path, command: str, unknown_args: List[str], translation_helper: Callable) -> int:
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
    # Add environment variables to suppress some noise and indicate managed mode
    env = os.environ.copy()
    env["TK_SILENCE_DEPRECATION"] = "1"
    env["GDS_GUI_MANAGED"] = "1"
    
    proc = subprocess.Popen([python_exe, script_path], 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            text=True, encoding='utf-8', start_new_session=True,
                            env=env)
    
    # Display PID for precise termination if needed
    tool_name = tool_instance.tool_name
    label_waiting_key = "label_waiting_gui"
    if tool_name == "FILEDIALOG": label_waiting_key = "label_waiting_selection"
    
    label_waiting = tool_instance.get_translation(label_waiting_key, f"Waiting for {tool_name} feedback via GUI")
    display_msg = f"{BOLD}{BLUE}{label_waiting}{RESET} (PID: {proc.pid})..."
    
    from logic.turing.display.manager import truncate_to_width, _get_configured_width
    width = _get_configured_width()
    if width > 0:
        display_msg = truncate_to_width(display_msg, width)
        
    sys.stdout.write(f"\r\033[K{display_msg}")
    sys.stdout.flush()

    stdout_content = []
    def read_stdout():
        for line in iter(proc.stdout.readline, ''): stdout_content.append(line)
        proc.stdout.close()
    t_stdout = threading.Thread(target=read_stdout, daemon=True)
    t_stdout.start()

    stderr_content = []
    def read_stderr():
        for line in iter(proc.stderr.readline, ''): stderr_content.append(line)
        proc.stderr.close()
    t_stderr = threading.Thread(target=read_stderr, daemon=True)
    t_stderr.start()

    parent_timeout = timeout + 300
    start_wait = time.time()
    
    # Path for add_time events
    added_time_dir = tool_instance.project_root / "data" / "run" / "added_time"
    added_time_dir.mkdir(parents=True, exist_ok=True)
    
    is_interrupted = False
    try:
        while proc.poll() is None:
            # 1. Check for add_time events
            try:
                for f in list(added_time_dir.glob(f"{proc.pid}_*.add")):
                    # Extract increment from filename
                    parts = f.stem.split('_')
                    if len(parts) >= 3:
                        try:
                            inc = int(parts[2])
                            parent_timeout += inc
                        except: pass
                    f.unlink() # Consume event
            except: pass

            # 2. Watchdog check
            if time.time() - start_wait > parent_timeout:
                proc.kill()
                sys.stdout.write("\r\033[K")
                sys.stdout.flush()
                t_stdout.join(timeout=2)
                t_stderr.join(timeout=2)
                return {"status": "timeout", "data": None}
            time.sleep(0.5)
        
        proc.wait() # Wait for process to exit
        t_stdout.join(timeout=2)
        t_stderr.join(timeout=2)
        stdout = "".join(stdout_content)
        stderr = "".join(stderr_content)
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
            # Instead of communicate, we wait for proc and join threads
            start_grace = time.time()
            while proc.poll() is None and time.time() - start_grace < 4:
                time.sleep(0.1)
            
            if proc.poll() is None:
                proc.kill()
            
            t_stdout.join(timeout=1)
            t_stderr.join(timeout=1)
            stdout = "".join(stdout_content)
            stderr = "".join(stderr_content)
        except:
            proc.kill()
            t_stdout.join(timeout=1)
            t_stderr.join(timeout=1)
            stdout = "".join(stdout_content)
            stderr = "".join(stderr_content)
        
        if not stdout:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            if is_interrupted:
                return {"status": "terminated", "data": None, "reason": "interrupted"}
            raise e

    sys.stdout.write("\r\033[K"); sys.stdout.flush()
    
    # DEBUG: See raw output
    sys.stderr.write(f"\n[DEBUG_MANAGER] Raw stdout length: {len(stdout)}\n")
    if stdout: sys.stderr.write(f"[DEBUG_MANAGER] Raw stdout lines: {stdout.splitlines()!r}\n")
    if stderr: sys.stderr.write(f"[DEBUG_MANAGER] Raw stderr: {stderr!r}\n")

    # Parse JSON result
    res = None
    for line in stdout.splitlines():
        if "GDS_GUI_RESULT_JSON:" in line:
            sys.stderr.write(f"[DEBUG_MANAGER] Found JSON line: {line!r}\n")
            try:
                # Find the start of JSON
                json_str = line.split("GDS_GUI_RESULT_JSON:")[1].strip()
                res = json.loads(json_str)
                sys.stderr.write(f"[DEBUG_MANAGER] Successfully parsed JSON: {res}\n")
                break
            except Exception as e: 
                sys.stderr.write(f"[DEBUG_MANAGER] JSON parse failed: {e}\n")
                pass
    
    if res:
        # If it was terminated, refine reason
        if res.get("status") == "terminated":
            if is_interrupted:
                res["reason"] = "interrupted"
            elif not res.get("reason"):
                res["reason"] = "stop" # Default for termination via flag
        return res
    
    # Filter stderr
    filtered_stderr = ""
    if stderr:
        noise_patterns = ["IMKClient subclass", "IMKInputSession subclass", "chose IMKClient_Legacy", "chose IMKInputSession_Legacy"]
        lines = stderr.splitlines()
        filtered_lines = [l for l in lines if not any(p in l for p in noise_patterns)]
        filtered_stderr = "\n".join(filtered_lines)

    # Hide debug prints unless specifically enabled
    from logic.config import get_setting
    if get_setting("gui_manager_debug", False):
        sys.stderr.write(f"DEBUG: GUI process {proc.pid} exited with code {proc.returncode}\n")
        if filtered_stderr: sys.stderr.write(f"DEBUG: GUI stderr: {filtered_stderr}\n")
    
    # Error fallback for crashes
    if proc.returncode != 0:
        sig_codes = [-15, -2, -9, -11, -6, 15, 2, 9, 11, 6, 143, 130, 137, 139, 134]
        if proc.returncode in sig_codes:
            return {"status": "terminated", "data": None, "reason": "signal"}
            
    return {"status": "error", "message": filtered_stderr or stderr or "No valid response from GUI"}

def run_file_fallback(tool_instance, initial_content: str, timeout: int) -> Optional[str]:
    """
    Core logic for text-file based GUI fallback in sandboxed environments.
    Returns the content of the file if modified, or None if timeout/interrupted.
    """
    from logic.config import get_color
    from logic.gui.engine import get_sandbox_type
    from logic.utils import cleanup_old_files
    import platform
    
    BOLD, BLUE, GREEN, RED, YELLOW, RESET = get_color("BOLD", "\033[1m"), get_color("BLUE", "\033[34m"), get_color("GREEN", "\033[32m"), get_color("RED", "\033[31m"), get_color("YELLOW", "\033[33m"), get_color("RESET", "\033[0m")
    
    # 2. Setup paths - use tool's data/input directory
    input_dir = tool_instance.get_data_dir() / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    ts = time.strftime("%Y%m%d_%H%M%S")
    rand_hash = hashlib.md5(str(random.random()).encode()).hexdigest()[:6]
    input_file = input_dir / f"input_{ts}_{rand_hash}.txt"
    
    # 2. Create initial empty file (Hint will be in terminal)
    with open(input_file, 'w', encoding='utf-8') as f:
        f.write("")
    initial_mtime = input_file.stat().st_mtime
    
    # Cleanup old files (limit 1000)
    cleanup_old_files(input_dir, "input_*.txt", limit=1000)
    
    # 3. Inform user
    sb_type = get_sandbox_type()
    # Erase the "Waiting for GUI" line if it exists
    sys.stdout.write("\r\033[K")
    print(f"{BOLD}{YELLOW}Sandbox detected{RESET}: {sb_type} (GUI physical blocking)")
    
    # Display Hint if provided
    _ = tool_instance.get_translation
    if initial_content:
        hint_label = _("fallback_hint_label", "Hint")
        WHITE = get_color("WHITE", "\033[37m")
        print(f"{BOLD}{BOLD}{hint_label}{RESET}: {initial_content}")

    try:
        rel_path = str(input_file.relative_to(tool_instance.project_root))
    except ValueError:
        rel_path = str(input_file)
        
    until_ts = time.time() + timeout
    until_time = time.strftime("%H:%M:%S", time.localtime(until_ts))
    
    waiting_msg_tmpl = _("fallback_waiting_until", "Waiting for {tool_name} feedback via file: {path}, until {until_time}...")
    
    # Bold the file path
    bold_path = f"{BOLD}{rel_path}{RESET}"
    display_msg = waiting_msg_tmpl.format(tool_name=tool_instance.tool_name, path=bold_path, until_time=until_time)
    
    # Split for color styling if prefix exists
    if ":" in display_msg:
        prefix, rest = display_msg.split(":", 1)
        # Ensure prefix includes the colon
        full_msg = f"{BOLD}{BLUE}{prefix}:{RESET}{rest}"
    else:
        full_msg = f"{BOLD}{BLUE}{display_msg}{RESET}"
    
    print(full_msg, flush=True)
    
    # 4. Polling loop
    bell_path = tool_instance.project_root / "logic" / "gui" / "asset" / "audio" / "bell.mp3"
    
    # Try to get focus interval from config
    fi = 90
    try:
        from logic.config import get_global_config
        fi = get_global_config().get("focus_interval", 90)
    except: pass
    if fi > 0 and fi < 90: fi = 90
    
    last_focus = time.time() # Start from now to avoid immediate bell
    
    try:
        while time.time() < until_ts:
            now = time.time()
            # Periodic Audio Alert (Focus replacement)
            if fi > 0 and now - last_focus >= fi:
                from logic.gui.engine import play_notification_bell
                play_notification_bell(tool_instance.project_root)
                last_focus = now
                
            if input_file.exists():
                if input_file.stat().st_mtime > initial_mtime:
                    with open(input_file, 'r', encoding='utf-8') as f:
                        content = f.read().strip()
                    if content: # Any non-empty content is accepted
                        success_label = _("label_successfully_received", "Successfully received")
                        print(f"{BOLD}{GREEN}{success_label}{RESET} from file: {content}", flush=True)
                        return content
            time.sleep(1)
    except KeyboardInterrupt:
        # User explicitly interrupted
        interrupted_label = _("msg_interrupted", "Interrupted")
        print(f"\r\033[K{BOLD}{RED}{interrupted_label}{RESET}")
        return "__FALLBACK_INTERRUPTED__"
        
    # Timeout case
    timeout_label = _("fallback_timed_out", "Fallback timed out")
    run_again_hint = _("fallback_run_again", "Please run {tool_name} again.")
    print(f"\r\033[K{BOLD}{RED}{timeout_label}{RESET}. {run_again_hint.format(tool_name=tool_instance.tool_name)}")
    return "__FALLBACK_TIMEOUT__"

def handle_gui_stop_command(tool_name: str, project_root: Path, unknown_args: List[str], translation_helper: Callable) -> int:
    return handle_gui_remote_command(tool_name, project_root, "stop", unknown_args, translation_helper)
