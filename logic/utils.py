import os
import sys
import re
import json
import time
import subprocess
import unicodedata
import difflib
import builtins
import platform
from pathlib import Path

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
    
    # Check if bin/PYTHON exists.
    project_root = Path(__file__).resolve().parent.parent
    python_bin = project_root / "bin" / "PYTHON"
    
    # Add a blank line before the error
    print("")
    
    error_label = _("label_error", "Error")
    msg = _("err_python_not_found", "Python tool '{version}' not found, cannot launch {tool_name} GUI.").format(version=version, tool_name=tool_name)
    print(f"{BOLD}{RED}{error_label}{RESET}: {msg}", flush=True) # Only "Error" is red and bold
    
    # Heuristic: if we are in a process where PYTHON tool might have already run,
    # or if bin/PYTHON exists, we suggest following PYTHON's instructions.
    # We use a simple environment variable to track if PYTHON has already printed instructions.
    if os.environ.get("PYTHON_INSTRUCTIONS_PRINTED") == "1" or python_bin.exists():
        print(_("err_tool_depends_on_python_follow", "The tool '{tool_name}' depends on the PYTHON tool. Please follow the PYTHON tool instructions above and then run: {tool_name} setup").format(tool_name=tool_name), flush=True)
    else:
        print(_("err_python_not_found_hint_2", "Please run: TOOL install PYTHON"), flush=True)
        print(_("err_python_not_found_hint_3", "Then run: PYTHON --py-install {version}").format(version=version), flush=True)
        
        setup_path = script_dir / "setup.py"
        if setup_path.exists():
            print(_("err_python_not_found_hint_4", "Finally, run tool's setup: {tool_name} setup").format(tool_name=tool_name), flush=True)
        else:
            print(_("err_python_not_found_hint_4", "Finally, run tool's setup: TOOL install {tool_name}").format(tool_name=tool_name), flush=True)

# Global state for RTL mode
_GLOBAL_RTL_MODE = False
_original_print = builtins.print

def _init_rtl_mode():
    """Initializes RTL mode based on environment or configuration."""
    global _GLOBAL_RTL_MODE
    current_lang = os.environ.get("TOOL_LANGUAGE")
    if not current_lang:
        try:
            # logic/utils.py is in logic/
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = project_root / "data" / "global_config.json"
            
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    current_lang = config.get("language")
        except Exception:
            pass
    
    if current_lang in ["ar", "he", "fa"]:
        _GLOBAL_RTL_MODE = True

def set_rtl_mode(enabled: bool):
    """Sets the global RTL mode for printing and formatting."""
    global _GLOBAL_RTL_MODE
    _GLOBAL_RTL_MODE = enabled

def get_rtl_mode() -> bool:
    """Returns the current global RTL mode."""
    return _GLOBAL_RTL_MODE

def smart_print(*args, **kwargs):
    """
    An enhanced print function that automatically adds RTL markers 
    if the global RTL mode is enabled.
    """
    is_rtl = kwargs.pop('is_rtl', _GLOBAL_RTL_MODE)
    
    if not is_rtl:
        return _original_print(*args, **kwargs)
    
    # Debug mode if env var is set
    debug_rtl = os.environ.get("DEBUG_RTL") == "1"
    # Force flip mode using RLO (\u202e) instead of RLE (\u202b)
    force_flip = os.environ.get("FORCE_RTL_FLIP") == "1"
    marker = "\u202e" if force_flip else "\u202b"
    
    # Process args to wrap in RTL markers
    new_args = []
    for arg in args:
        val = str(arg)
        if "\n" in val:
            # For multi-line strings, wrap each line to ensure consistent rendering across terminals
            # Using \u200f (RLM), marker and \u202c (PDF)
            wrapped_lines = []
            for line in val.split("\n"):
                wrapped = f"\u200f{marker}{line}\u202c"
                if debug_rtl:
                    # Show hex for the first few chars to verify
                    hex_prefix = ":".join(f"{ord(c):04x}" for c in wrapped[:5])
                    _original_print(f"[DEBUG RTL Line Start Hex: {hex_prefix}...]")
                wrapped_lines.append(wrapped)
            new_args.append("\n".join(wrapped_lines))
        else:
            wrapped = f"\u200f{marker}{val}\u202c"
            if debug_rtl:
                hex_prefix = ":".join(f"{ord(c):04x}" for c in wrapped[:5])
                _original_print(f"[DEBUG RTL Single Hex: {hex_prefix}...]")
            new_args.append(wrapped)
            
    return _original_print(*new_args, **kwargs)

# Automatically override built-in print to support RTL
builtins.print = smart_print

_init_rtl_mode()

def get_display_width(text):
    """
    Calculate the display width of a string, considering multi-byte characters
    and ignoring ANSI escape sequences and RTL markers.
    """
    # Strip ANSI escape sequences and RTL markers (\u202b, \u202c, \u200f, \u202e)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|[\u202b\u202c\u200f\u202e]')
    stripped_text = ansi_escape.sub('', text)
    
    width = 0
    for char in stripped_text:
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

def truncate_to_display_width(text, max_width):
    """
    Truncate a string to a specific display width, taking multi-byte characters 
    and ANSI escape sequences/RTL markers into account.
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
        # Ignore RTL markers for width calculation
        if char in ('\u202b', '\u202c'):
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
    # terminal's BiDi support (triggered by \u202b) to flip the entire line.
    display_headers = headers
    display_rows = []
    for row in rows:
        full_row = list(row) + [""] * (num_cols - len(row))
        display_rows.append(full_row)

    # Box-drawing character and bracket mirroring for RTL
    # When the terminal flips the line visually, these characters should be mirrored
    # to maintain the correct box look.
    mirror_map = {
        "╔": "╗", "╗": "╔",
        "╚": "╝", "╝": "╚",
        "╠": "╣", "╣": "╠",
        "(": ")", ")": "(",
        "[": "]", "]": "[",
        "{": "}", "}": "{",
        "<": ">", ">": "<",
    }
    
    def mirror_line(line):
        if not is_rtl:
            return line
        res = ""
        i = 0
        while i < len(line):
            if line[i] == '\x1B':
                # Skip ANSI escape sequence
                j = i
                while j < len(line) and not ('A' <= line[j] <= 'Z' or 'a' <= line[j] <= 'z'):
                    j += 1
                if j < len(line):
                    res += line[i:j+1]
                    i = j + 1
                    continue
            res += mirror_map.get(line[i], line[i])
            i += 1
        return res

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
        
        return mirror_line("║" + "║".join(parts) + "║")

    # Construct borders
    top_border = mirror_line("╔" + "╦".join(["═" * w for w in col_widths]) + "╗")
    sep_border = mirror_line("╠" + "╬".join(["═" * w for w in col_widths]) + "╣")
    bottom_border = mirror_line("╚" + "╩".join(["═" * w for w in col_widths]) + "╝")

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

def format_seconds(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 0: return "unknown"
    if seconds < 60: return f"{int(seconds)}s"
    if seconds < 3600: return f"{int(seconds//60)}m{int(seconds%60)}s"
    return f"{int(seconds//3600)}h{int((seconds%3600)//60)}m"

def get_logic_dir(base_dir):
    """Returns the logic directory path for a given base directory."""
    return Path(base_dir) / "logic"

def run_with_progress(cmd, prefix, worker_id=None, manager=None, interval=0.5):
    """
    Runs a command and parses its stderr for percentage progress.
    Updates an erasable line (via sys.stdout.write or MultiLineManager).
    Ensures NO raw output from the command leaks to the terminal.
    Uses simple text format: 'Prefix: XX% (Speed) [Elapsed: t1, Left: t2]'
    """
    from logic.config import get_setting
    decimal_places = get_setting("progress_decimal_places", 1)
    fmt = f"{{:.{decimal_places}f}}%"

    if cmd[0] == "curl":
        # Force a simple numeric progress if possible, or just parse default
        cmd = [arg for arg in cmd if arg not in ["-#", "--progress-bar", "-s", "--silent"]]
    elif "git" in cmd[0] and "push" in cmd:
        if "--progress" not in cmd:
            cmd.append("--progress")

    # Initial progress display
    initial_text = f"{prefix}: " + fmt.format(0.0)
    if manager and worker_id:
        manager.update(worker_id, initial_text)
    else:
        sys.stdout.write(f"\r\033[K{initial_text}")
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
                partial_line = ""
                if not line:
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
                    percent_str = fmt.format(max_percent)
                    
                    # Time calculation
                    t1 = curr_time - start_time
                    p = max_percent / 100.0
                    if p > 0:
                        t2 = t1 / p - t1
                        t2_str = format_seconds(t2)
                    else:
                        t2_str = "unknown"
                    t1_str = format_seconds(t1)
                    
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
                        sys.stdout.write(f"\r\033[K{status_text}")
                        sys.stdout.flush()
                    last_print = curr_time
            else:
                partial_line += char
    finally:
        process.wait()
    
    if process.returncode == 0:
        total_time = format_seconds(time.time() - start_time)
        final_text = f"{prefix}: 100% ({total_time})"
        if manager and worker_id:
            manager.update(worker_id, final_text)
        else:
            sys.stdout.write(f"\r\033[K{final_text}\n")
            sys.stdout.flush()
    else:
        if not manager:
            sys.stdout.write(f"\r\033[K")
            sys.stdout.flush()
        
    return process.returncode == 0
