"""Progress tracking, ETA calculation, and retry decorator."""
import os
import sys
import re
import time
import subprocess
from logic.utils.display import format_seconds, truncate_to_display_width


def retry(max_attempts=3, backoff=1.0, retryable_exceptions=(Exception,), retryable_status_codes=(500, 502, 503, 504)):
    """
    Decorator for retrying a function on transient failures.

    Args:
        max_attempts: Maximum number of attempts (default 3).
        backoff: Seconds to wait between retries (default 1.0).
        retryable_exceptions: Tuple of exception types to retry on.
        retryable_status_codes: HTTP status codes that trigger a retry
            (only checked if the return value has a `status_code` attribute).
    """
    import functools
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    if hasattr(result, 'status_code') and result.status_code in retryable_status_codes:
                        if attempt < max_attempts - 1:
                            time.sleep(backoff)
                            continue
                    return result
                except retryable_exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(backoff)
                    else:
                        raise
            raise last_exception
        return wrapper
    return decorator


def calculate_eta(current, total, elapsed_time):
    """
    Calculate estimated remaining time.
    :param current: Current progress (count)
    :param total: Total expected (count)
    :param elapsed_time: Seconds elapsed so far
    :return: Tuple of (elapsed_str, remaining_str) formatted as MM:SS or HH:MM:SS
    """
    def format_duration(seconds):
        if seconds < 0: return "??:??"
        if seconds >= 3600:
            return time.strftime("%H:%M:%S", time.gmtime(seconds))
        return time.strftime("%M:%S", time.gmtime(seconds))

    elapsed_str = format_duration(elapsed_time)
    
    if current <= 0 or total <= 0:
        return elapsed_str, "??:??"
    
    if current >= total:
        return elapsed_str, "00:00"
        
    rate = current / elapsed_time if elapsed_time > 0 else 0
    if rate <= 0:
        return elapsed_str, "??:??"
        
    remaining_seconds = (total - current) / rate
    remaining_str = format_duration(remaining_seconds)
    
    return elapsed_str, remaining_str


def run_with_progress(cmd, prefix, worker_id=None, manager=None, interval=0.5):
    """
    Runs a command and parses its stderr for percentage progress.
    Updates an erasable line (via sys.stdout.write or MultiLineManager).
    Ensures NO raw output from the command leaks to the terminal.
    Returns: (success, error_message)
    """
    from logic.config import get_setting
    from logic.turing.display.manager import _get_configured_width
    
    decimal_places = get_setting("progress_decimal_places", 0)
    fmt = f"{{:.{decimal_places}f}}%"
    full_error_output = []

    is_push = "git" in cmd[0] and "push" in cmd
    if cmd[0] == "curl":
        cmd = [arg for arg in cmd if arg not in ["-#", "--progress-bar", "-s", "--silent"]]
    elif is_push:
        if "--progress" not in cmd:
            cmd.append("--progress")

    initial_text = f"{prefix}: " + (fmt.format(0.0) if not is_push else "...")
    if manager and worker_id:
        manager.update(worker_id, initial_text)
    else:
        width = _get_configured_width()
        if width > 0:
            display_text = truncate_to_display_width(initial_text, max(1, width - 2))
        else:
            display_text = initial_text
        sys.stdout.write(f"\r\033[K{display_text}")
        sys.stdout.flush()

    env = os.environ.copy()
    env["LC_ALL"] = "C"
    
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.DEVNULL, 
        stderr=subprocess.PIPE, 
        text=True, 
        bufsize=1, 
        env=env,
        universal_newlines=True
    )
    
    start_time = time.time()
    last_print = 0
    max_percent = 0.0
    re_percent = re.compile(r'(\d+(?:\.\d+)?)%')
    
    try:
        partial_line = ""
        while True:
            char = process.stderr.read(1)
            if not char:
                break
            
            if char in ['\r', '\n']:
                line = partial_line.strip()
                full_error_output.append(partial_line)
                partial_line = ""
                if not line:
                    if is_push:
                        pass
                    else:
                        continue
                
                match = re_percent.search(line)
                if match:
                    try:
                        curr_percent = float(match.group(1))
                        max_percent = max(max_percent, curr_percent)
                    except ValueError: pass
                elif cmd[0] == "curl":
                    parts = line.split()
                    if len(parts) >= 1 and parts[0].isdigit():
                        try:
                            curr_percent = float(parts[0])
                            max_percent = max(max_percent, curr_percent)
                        except ValueError: pass

                curr_time = time.time()
                if curr_time - last_print >= interval:
                    t1 = curr_time - start_time
                    t1_str = format_seconds(t1)

                    if is_push and max_percent == 0:
                        status_text = f"{prefix}... ({t1_str})"
                    else:
                        percent_str = fmt.format(max_percent)
                        t1_str, t2_str = calculate_eta(max_percent, 100.0, t1)
                        time_info = f" [{t1_str}<{t2_str}]"
                        
                        extra = ""
                        speed_match = re.search(r'(\d+\.?\d*\s*[KMG]B/s)', line)
                        if speed_match:
                            extra = f" ({speed_match.group(1)})"
                        elif cmd[0] == "curl":
                            parts = line.split()
                            if len(parts) >= 7:
                                for p_arg in parts[6:]:
                                    if any(c.isdigit() for c in p_arg) and any(u in p_arg.upper() for u in ['K', 'M', 'G']):
                                        extra = f" ({p_arg}/s)"
                                        break
                        
                        status_text = f"{prefix}: {percent_str}{extra}{time_info}"

                    if manager and worker_id:
                        manager.update(worker_id, status_text)
                    else:
                        width = _get_configured_width()
                        if width > 0:
                            display_text = truncate_to_display_width(status_text, max(1, width - 2))
                        else:
                            display_text = status_text
                        sys.stdout.write(f"\r\033[K{display_text}")
                        sys.stdout.flush()
                    last_print = curr_time
            else:
                partial_line += char
    finally:
        process.wait()
    
    error_msg = "".join(full_error_output).strip()
    if process.returncode == 0:
        total_time = format_seconds(time.time() - start_time)
        final_text = f"{prefix}: 100% ({total_time})"
        if manager and worker_id:
            manager.update(worker_id, final_text)
        else:
            width = _get_configured_width()
            display_text = truncate_to_display_width(final_text, max(1, width - 1))
            sys.stdout.write(f"\r\033[K{display_text}")
            sys.stdout.flush()
        return True, ""
    else:
        if not manager:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
        
        simplified_error = error_msg.splitlines()[-1] if error_msg.splitlines() else "Unknown error"
        return False, simplified_error
