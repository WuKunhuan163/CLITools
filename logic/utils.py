import os
import sys
import re
import time
import subprocess
import unicodedata
import shutil
import builtins
import platform
from pathlib import Path

def calculate_eta(current, total, elapsed_time):
    """
    Calculate estimated remaining time.
    :param current: Current progress (count)
    :param total: Total expected (count)
    :param elapsed_time: Seconds elapsed so far
    :return: Tuple of (elapsed_str, remaining_str) formatted as MM:SS or HH:MM:SS
    """
    import time
    
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

def get_system_tag():
    """Detect current system tag for Python downloads."""
    system = sys.platform
    machine = platform.machine().lower()
    if system == "darwin":
        return "macos-arm64" if "arm" in machine or "aarch64" in machine else "macos"
    if system == "linux":
        try:
            # Check for musl (alpine)
            with open("/etc/os-release", "r") as f:
                if "alpine" in f.read().lower(): return "linux64-musl"
        except: pass
        return "linux64"
    if system == "win32":
        if "arm" in machine: return "windows-arm64"
        return "windows-amd64" if "64" in machine else "windows-x86"
    return "unknown"

def regularize_version_name(version, platform=None):
    """Standardize version name to 'X.Y.Z-platform' (no 'python' prefix)."""
    v = str(version)
    if v.startswith("python"):
        v = v[6:]
    if "-" in v:
        v = v.split("-")[0]
    plat = platform or get_system_tag()
    return f"{v}-{plat}"

def extract_resource(source_zst, target_dir, silent=False):
    """Integrated zst + tar extraction."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if not silent:
        print(f"Extracting {source_zst.name}...")
    
    if sys.platform != "win32":
        try:
            # Try tar with built-in zstd support
            res = subprocess.run(["tar", "--zstd", "-xf", str(source_zst), "-C", str(target_dir)], capture_output=True)
            if res.returncode == 0: return True
            # Fallback: unzstd pipe
            cmd = f"unzstd -c {source_zst} | tar -xf - -C {target_dir}"
            res = subprocess.run(cmd, shell=True, capture_output=True)
            if res.returncode == 0: return True
        except: pass
    return False

def print_missing_tool_error(tool_name, dep_name, script_dir, translation_func=None):
    """Unified error reporting for missing tool dependency."""
    _ = translation_func or (lambda k, d: d)
    
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")
    
    error_label = _("label_error", "Error")
    print(f"{BOLD}{RED}{error_label}{RESET}: " + _("err_tool_not_found", "Tool '{dep_name}' not found, required by '{tool_name}'.").format(dep_name=dep_name, tool_name=tool_name), flush=True)
    print(_("err_tool_install_hint", "Please run: TOOL install {dep_name}").format(dep_name=dep_name), flush=True)
    
    setup_path = script_dir / "setup.py"
    if setup_path.exists():
        print(_("err_tool_setup_hint", "Finally, run tool's setup: {tool_name} setup").format(tool_name=tool_name), flush=True)
    else:
        print(_("err_tool_setup_hint", "Finally, run tool's setup: TOOL install {tool_name}").format(tool_name=tool_name), flush=True)

def print_python_not_found_error(tool_name, version, script_dir, translation_func=None):
    """Unified error reporting for missing Python version."""
    _ = translation_func or (lambda k, d: d)
    
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")
    
    error_label = _("label_error", "Error")
    msg = _("err_python_not_found", "Python tool '{version}' not found, cannot launch {tool_name} GUI.").format(version=version, tool_name=tool_name)
    sys.stdout.write(f"{BOLD}{RED}{error_label}{RESET}: {msg}\n")
    
    # Always show installation instructions if the version is not found
    sys.stdout.write(_("err_python_not_found_hint_2", "Please run: TOOL install PYTHON") + "\n")
    sys.stdout.write(_("err_python_not_found_hint_3", "Then run: PYTHON --py-install {version}").format(version=version) + "\n")
    
    # Add a hint about how to download if it's missing
    download_hint = _("err_python_download_hint", "To download a missing version: PYTHON --py-update --version {version}").format(version=version)
    sys.stdout.write(download_hint + "\n")
    
    setup_path = script_dir / "setup.py"
    if setup_path.exists():
        sys.stdout.write(_("err_python_not_found_hint_4", "Finally, run tool's setup: {tool_name} setup").format(tool_name=tool_name) + "\n")
    else:
        sys.stdout.write(_("err_python_not_found_hint_4", "Finally, run tool's setup: TOOL install {tool_name}").format(tool_name=tool_name) + "\n")
    sys.stdout.flush()

# Global state for RTL mode
_GLOBAL_RTL_MODE = False

def set_rtl_mode(enabled: bool):
    """Sets the global RTL mode for printing and formatting."""
    global _GLOBAL_RTL_MODE
    _GLOBAL_RTL_MODE = enabled

def get_rtl_mode() -> bool:
    """Returns the current global RTL mode."""
    return _GLOBAL_RTL_MODE

def get_display_width(text):
    """
    Calculate the display width of a string, considering multi-byte characters
    and ignoring ANSI escape sequences, RTL markers, and control characters.
    """
    # Strip ANSI escape sequences and RTL markers (\u202b, \u202c, \u200f, \u202e)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|[\u202b\u202c\u200f\u202e]')
    stripped_text = ansi_escape.sub('', text)
    
    width = 0
    for char in stripped_text:
        # Ignore control characters like \r, \n, \t
        if ord(char) < 32:
            continue
            
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('W', 'F'):
            width += 2
        else:
            width += 1
            
    # Heuristic for Arabic ligatures (like Lam-Alef) which take 2 chars in code 
    # but often only 1 cell on screen in some terminals. 
    # If we treat them as 1 cell in width calculation, we add more padding spaces.
    for k in range(len(stripped_text) - 1):
        if stripped_text[k] == '\u0644' and stripped_text[k+1] in ['\u0627', '\u0622', '\u0623', '\u0625']:
            width -= 1
            
    return width

def print_terminal_width_separator(width=None):
    """Prints a separator line of '=' characters matching the terminal width."""
    if width is None:
        from logic.turing.display.manager import _get_configured_width
        width = _get_configured_width()
    if width and width > 0:
        sys.stdout.write("\r\033[K" + "=" * width + "\n")
        sys.stdout.flush()

def truncate_to_display_width(text, max_width):
    """
    Truncate a string to a specific display width, taking multi-byte characters 
    and ANSI escape sequences/RTL markers/control characters into account.
    """
    current_width = 0
    result = ""
    i = 0
    while i < len(text):
        if text[i] == '\x1B':
            j = i
            while j < len(text) and not ('A' <= text[j] <= 'Z' or 'a' <= text[j] <= 'z'):
                j += 1
            if j < len(text):
                result += text[i:j+1]
                i = j + 1
                continue
        
        char = text[i]
        # Ignore RTL markers and control characters for width calculation
        if char in ('\u202b', '\u202c') or ord(char) < 32:
            result += char
            i += 1
            continue

        eaw = unicodedata.east_asian_width(char)
        char_width = 2 if eaw in ('W', 'F') else 1
        
        if current_width + char_width > max_width:
            break
        result += char
        current_width += char_width
        i += 1
    return result

def get_rate_color(rate_str, colors=None):
    """
    Returns the ANSI color code for a given completion rate string.
    Thresholds: <60% Red, 60-90% Yellow, 90-100% Blue, 100% Green.
    """
    if not colors:
        BOLD = "\033[1m"
        GREEN = "\033[32m"
        BLUE = "\033[34m"
        YELLOW = "\033[33m"
        RED = "\033[31m"
        RESET = "\033[0m"
    else:
        BOLD = colors.get("BOLD", "")
        GREEN = colors.get("GREEN", "")
        BLUE = colors.get("BLUE", "")
        YELLOW = colors.get("YELLOW", "")
        RED = colors.get("RED", "")
        RESET = colors.get("RESET", "")

    try:
        rate_val = float(rate_str.strip('%'))
        if rate_val >= 100: return f"{BOLD}{GREEN}"
        if rate_val >= 90: return f"{BOLD}{BLUE}"
        if rate_val >= 60: return f"{BOLD}{YELLOW}"
        return f"{BOLD}{RED}"
    except Exception:
        return ""

def format_table(headers, rows, max_width=None, save_dir="tmp", full_display_cols=None):
    """
    Formats a table with double-line box-drawing characters and optional truncation.
    If truncated, saves the full table to a Markdown file.
    full_display_cols: List of header names that should be prioritized for full display.
    """
    if not headers or not rows:
        return "", None

    num_cols = len(headers)
    full_display_cols = full_display_cols or []
    is_rtl = get_rtl_mode()
    
    # NOTE: We do NOT manually reverse columns here because we rely on the 
    # terminal's BiDi support to flip the entire line.
    display_headers = headers
    display_rows = []
    for row in rows:
        full_row = list(row) + [""] * (num_cols - len(row))
        display_rows.append(full_row)

    # Calculate initial column widths based on maximum content width
    # We add 2 for padding (one space on each side)
    col_widths = [get_display_width(str(h)) + 2 for h in display_headers]
    for row in display_rows:
        for i in range(num_cols):
            col_widths[i] = max(col_widths[i], get_display_width(str(row[i])) + 2)

    # Calculate overhead from borders: num_cols + 1 vertical bars
    border_overhead = num_cols + 1
    
    is_truncated = False
    if max_width:
        total_width_with_borders = sum(col_widths) + border_overhead
        if total_width_with_borders > max_width:
            is_truncated = True
            
            # Ensure each column has at least enough width for its header or a minimum
            available_for_content = max_width - border_overhead
            new_col_widths = [0] * num_cols
            remaining_width = available_for_content
            
            # First pass: assign full width to prioritized columns
            for i in range(num_cols):
                h_name = display_headers[i]
                if h_name in full_display_cols:
                    take = min(col_widths[i], remaining_width - (num_cols - 1 - i) * 4)
                    take = max(take, 4)
                    new_col_widths[i] = take
                    remaining_width -= take
            
            # Second pass: assign minimum widths to remaining columns
            min_widths = []
            for i in range(num_cols):
                if new_col_widths[i] > 0:
                    min_widths.append(new_col_widths[i])
                    continue
                # Header width + padding
                h_w = get_display_width(str(display_headers[i])) + 2
                min_widths.append(min(h_w, 10)) # Cap min width to 10
            
            total_min_width = sum(min_widths)
            
            # Third pass: distribute remaining width
            for i in range(num_cols):
                if new_col_widths[i] > 0:
                    continue
                    
                min_w = min_widths[i]
                cols_left_to_fill = sum(1 for j in range(i+1, num_cols) if new_col_widths[j] == 0)
                needed_for_others = sum(min_widths[j] for j in range(i+1, num_cols) if new_col_widths[j] == 0)
                
                if cols_left_to_fill == 0:
                    new_col_widths[i] = max(min_w, remaining_width)
                else:
                    ideal_w = col_widths[i]
                    take = min(ideal_w, remaining_width - needed_for_others)
                    take = max(take, min_w)
                    new_col_widths[i] = take
                    remaining_width -= take
            col_widths = new_col_widths

    def get_data_line(data_row, widths):
        parts = []
        for i in range(num_cols):
            val_str = str(data_row[i])
            w = widths[i]
            # Content width is w - 2 (for padding)
            content_w = w - 2
                
            if get_display_width(val_str) > content_w:
                if content_w > 3:
                    display_str = truncate_to_display_width(val_str, content_w - 3) + "..."
                else:
                    display_str = truncate_to_display_width(val_str, content_w)
            else:
                display_str = val_str
            
            padding = " " * (content_w - get_display_width(display_str))
            parts.append(f" {display_str}{padding} ")
        
        return "║" + "║".join(parts) + "║"

    # Construct borders
    top_border = "╔" + "╦".join(["═" * w for w in col_widths]) + "╗"
    sep_border = "╠" + "╬".join(["═" * w for w in col_widths]) + "╣"
    bottom_border = "╚" + "╩".join(["═" * w for w in col_widths]) + "╝"

    formatted_lines = []
    formatted_lines.append(top_border)
    formatted_lines.append(get_data_line(display_headers, col_widths))
    formatted_lines.append(sep_border)
    for row in display_rows:
        formatted_lines.append(get_data_line(row, col_widths))
    formatted_lines.append(bottom_border)

    report_path = None
    if is_truncated:
        project_root = Path(__file__).resolve().parent.parent
        report_root = project_root / "data" / "table" / save_dir
        report_root.mkdir(parents=True, exist_ok=True)
        
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_root / f"table_report_{timestamp}.md"
        
        md_lines = []
        md_lines.append("| " + " | ".join(headers) + " |")
        md_lines.append("| " + " | ".join(["---"] * num_cols) + " |")
        for row in rows:
            md_lines.append("| " + " | ".join([str(v) for v in row]) + " |")
        
        try:
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write("\n".join(md_lines))
            report_path = str(report_file)
            cleanup_old_files(report_root, "*.md", limit=100)
        except Exception:
            pass

    return "\n".join(formatted_lines), report_path

def save_list_report(items, save_dir="list", filename_prefix="list_report", limit=100):
    """
    Saves a list of items to a Markdown file in data/list/{save_dir}.
    Cleans up old reports if limit is exceeded.
    Returns the path to the saved file.
    """
    project_root = Path(__file__).resolve().parent.parent
    report_root = project_root / "data" / "list" / save_dir
    report_root.mkdir(parents=True, exist_ok=True)
    
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_root / f"{filename_prefix}_{timestamp}.md"
    
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(f"- {item}\n")
        cleanup_old_files(report_root, "*.md", limit=limit)
        return str(report_file)
    except Exception:
        return None

def cleanup_old_files(target_dir, pattern="*", limit=100, batch_size=None):
    """
    Cleans up old files in a directory if the limit is exceeded.
    Deletes the oldest batch_size files (default: limit // 2).
    """
    try:
        target_path = Path(target_dir)
        if not target_path.exists():
            return
            
        if batch_size is None:
            batch_size = max(1, limit // 2)
            
        files = sorted(list(target_path.glob(pattern)), key=os.path.getmtime)
        if len(files) > limit:
            for i in range(min(len(files), batch_size)):
                try:
                    files[i].unlink(missing_ok=True)
                except Exception:
                    pass
    except Exception:
        pass

def cleanup_project_patterns(root_dir, patterns=None):
    """
    Recursively delete specified patterns (like .DS_Store, __pycache__) across the project.
    """
    if patterns is None:
        patterns = [".DS_Store", "__pycache__"]
    
    root_path = Path(root_dir)
    for pattern in patterns:
        if pattern == "__pycache__":
            # Recursively find all __pycache__ directories
            for p in root_path.rglob("__pycache__"):
                if p.is_dir():
                    try: shutil.rmtree(p)
                    except: pass
        else:
            # Recursively find and delete files matching the pattern
            for p in root_path.rglob(pattern):
                try:
                    if p.is_dir(): shutil.rmtree(p)
                    else: p.unlink()
                except: pass

def format_seconds(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 0: return "unknown"
    if seconds < 60: return f"{int(seconds)}s"
    if seconds < 3600: return f"{int(seconds//60)}m{int(seconds%60)}s"
    return f"{int(seconds//3600)}h{int((seconds%3600)//60)}m"

def get_python_tool_exec():
    """Find the PYTHON tool's executable path."""
    project_root = Path(__file__).resolve().parent.parent
    python_tool_dir = project_root / "tool" / "PYTHON"
    if not python_tool_dir.exists():
        return None
    
    # Try importing from tool.PYTHON.logic.utils
    try:
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))
        from tool.PYTHON.logic.utils import get_python_exec as gpe
        res = gpe()
        if res == "python3":
            return None
        return res
    except:
        return None

def get_python_exec():
    """Alias for get_python_tool_exec for backward compatibility."""
    return get_python_tool_exec()

def check_and_reexecute_with_python(tool_name, version=None):
    """
    Ensure the current script is running with the correct PYTHON tool executable.
    If not, re-execute. If PYTHON is missing, print helpful error and exit.
    """
    if version is None:
        from logic.config import get_setting
        version = get_setting("default_python_version", "3.11.14")
        
    project_root = Path(__file__).resolve().parent.parent
    py_exec = get_python_tool_exec()
    
    if py_exec and sys.executable != py_exec:
        # Re-execute
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
        os.execve(py_exec, [py_exec] + sys.argv, env)
    
    if not py_exec:
        # PYTHON tool missing or not operational
        print_python_not_found_error(tool_name, version, project_root / "tool" / tool_name)
        sys.exit(1)

def get_logic_dir(base_dir):
    """Returns the logic directory path for a given base directory."""
    return Path(base_dir) / "logic"

def find_project_root(start_path: Path) -> Path:
    """
    Robustly find the project root from any starting path.
    Look for indicators unique to the root of AITerminalTools.
    """
    curr = start_path.resolve()
    if curr.is_file():
        curr = curr.parent
    
    # Primary indicator: bin/TOOL and tool.json
    temp_curr = curr
    while temp_curr != temp_curr.parent:
        if (temp_curr / "bin" / "TOOL").exists() and (temp_curr / "tool.json").exists():
            return temp_curr
        temp_curr = temp_curr.parent
        
    # Secondary indicator: tool.json + logic/ + tool/ (for cases where bin/ might be missing or different)
    temp_curr = curr
    while temp_curr != temp_curr.parent:
        if (temp_curr / "tool.json").exists() and (temp_curr / "logic").is_dir() and (temp_curr / "tool").is_dir():
            # Ensure it's not a subtool dir (which might have tool.json but parent is 'tool')
            if temp_curr.parent.name != "tool":
                return temp_curr
        temp_curr = temp_curr.parent
        
    return curr # Fallback

def get_tool_module_path(tool_dir: Path, project_root: Path) -> str:
    """Returns the python module path for a tool relative to project root."""
    try:
        rel = tool_dir.relative_to(project_root)
        return ".".join(rel.parts)
    except ValueError:
        return ""

def get_module_relative_path(module_name: str) -> str:
    """
    Translates a module name (e.g. 'logic.tool.base') to its relative path 
    from the project root (e.g. 'logic/tool/base.py' or 'logic/tool/base/').
    """
    path_parts = module_name.split('.')
    return os.path.join(*path_parts)

def run_with_progress(cmd, prefix, worker_id=None, manager=None, interval=0.5):
    """
    Runs a command and parses its stderr for percentage progress.
    Updates an erasable line (via sys.stdout.write or MultiLineManager).
    Ensures NO raw output from the command leaks to the terminal.
    Uses simple text format: 'Prefix: XX% (Speed) [Elapsed: t1, Left: t2]'
    Returns: (success, error_message)
    """
    from logic.config import get_setting
    from logic.turing.display.manager import _get_configured_width
    
    # Precision changed to 0 by default per user request
    decimal_places = get_setting("progress_decimal_places", 0)
    fmt = f"{{:.{decimal_places}f}}%"
    full_error_output = []

    is_push = "git" in cmd[0] and "push" in cmd
    if cmd[0] == "curl":
        # Force a simple numeric progress if possible, or just parse default
        cmd = [arg for arg in cmd if arg not in ["-#", "--progress-bar", "-s", "--silent"]]
    elif is_push:
        if "--progress" not in cmd:
            cmd.append("--progress")

    # Initial progress display
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
    
    # Start process with captured stderr. Use universal_newlines=True for easier string reading.
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
            # Read character by character to handle \r updates
            char = process.stderr.read(1)
            if not char:
                break
            
            if char in ['\r', '\n']:
                line = partial_line.strip()
                full_error_output.append(partial_line) # Capture all output for error reporting
                partial_line = ""
                if not line:
                    # Update anyway if pushing to show time
                    if is_push:
                        pass
                    else:
                        continue
                
                # Parse percentage
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

                # Update display at intervals
                curr_time = time.time()
                if curr_time - last_print >= interval:
                    # Time calculation
                    t1 = curr_time - start_time
                    t1_str = format_seconds(t1)

                    if is_push and max_percent == 0:
                        # Special handling for push: show elapsed time instead of 0%
                        status_text = f"{prefix}... ({t1_str})"
                    else:
                        percent_str = fmt.format(max_percent)
                        # Use centralized calculate_eta helper
                        t1_str, t2_str = calculate_eta(max_percent, 100.0, t1)
                        time_info = f" [{t1_str}<{t2_str}]"
                        
                        # Speed detection
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
                            # Use width-2 to be safe against wrapping
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
            sys.stdout.write(f"\r\033[K{display_text}\n")
            sys.stdout.flush()
        return True, ""
    else:
        if not manager:
            sys.stdout.write(f"\r\033[K")
            sys.stdout.flush()
        
        # Simplify error message
        simplified_error = error_msg.splitlines()[-1] if error_msg.splitlines() else "Unknown error"
        return False, simplified_error

def register_path(bin_dir):
    """Add bin directory to PATH in shell profiles."""
    import os
    from pathlib import Path
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    profiles = []
    if "zsh" in shell: profiles.append(home / ".zshrc")
    elif "bash" in shell:
        profiles.append(home / ".bash_profile")
        profiles.append(home / ".bashrc")
    else: profiles.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
    for profile in profiles:
        if profile.exists():
            try:
                with open(profile, 'r') as f: content = f.read()
                if str(bin_dir) not in content:
                    with open(profile, 'a') as f: f.write(export_cmd)
            except: pass

    if str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:" + os.environ["PATH"]

def print_success_status(action_msg):
    """
    Unified success status reporting.
    Prints green bold 'Successfully' followed by action message.
    Modified per user request: 'Successfully [action]' is all green bold.
    """
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")
    
    # Split action_msg into first word and rest
    parts = action_msg.split(" ", 1)
    if not parts:
        prefix = "Successfully"
        rest = ""
    else:
        # Check if first word is 'installed' or 'setup' etc.
        # But user wants 'Successfully installed' all green bold.
        prefix = f"Successfully {parts[0]}"
        rest = f" {parts[1]}" if len(parts) > 1 else ""
        
    print(f"\r\033[K{BOLD}{GREEN}{prefix}{RESET}{rest}", flush=True)

# New CPU monitoring function
def get_cpu_percent(interval=0.1):
    """
    Returns the current system-wide CPU utilization as a percentage.
    Requires psutil.
    """
    try:
        import psutil
        return psutil.cpu_percent(interval=interval)
    except ImportError:
        return 0.0
    except Exception:
        return 0.0
