"""Display, formatting, and terminal output utilities."""
import sys
import re
import unicodedata
from pathlib import Path
from logic.utils.cleanup import cleanup_old_files

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
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|[\u202b\u202c\u200f\u202e]')
    stripped_text = ansi_escape.sub('', text)
    
    width = 0
    for char in stripped_text:
        if ord(char) < 32:
            continue
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('W', 'F'):
            width += 2
        else:
            width += 1
            
    for k in range(len(stripped_text) - 1):
        if stripped_text[k] == '\u0644' and stripped_text[k+1] in ['\u0627', '\u0622', '\u0623', '\u0625']:
            width -= 1
            
    return width

def print_terminal_width_separator(width=None):
    """Prints a separator line of '=' characters matching the terminal width."""
    if width is None or not isinstance(width, int) or width <= 0:
        from logic.turing.display.manager import _get_configured_width
        width = _get_configured_width()
    if isinstance(width, int) and width > 0:
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
    else:
        BOLD = colors.get("BOLD", "")
        GREEN = colors.get("GREEN", "")
        BLUE = colors.get("BLUE", "")
        YELLOW = colors.get("YELLOW", "")
        RED = colors.get("RED", "")

    try:
        rate_val = float(rate_str.strip('%'))
        if rate_val >= 100: return f"{BOLD}{GREEN}"
        if rate_val >= 90: return f"{BOLD}{BLUE}"
        if rate_val >= 60: return f"{BOLD}{YELLOW}"
        return f"{BOLD}{RED}"
    except Exception:
        return ""

def format_seconds(seconds):
    """Format seconds into a human-readable string."""
    if seconds < 0: return "unknown"
    if seconds < 60: return f"{int(seconds)}s"
    if seconds < 3600: return f"{int(seconds//60)}m{int(seconds%60)}s"
    return f"{int(seconds//3600)}h{int((seconds%3600)//60)}m"

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
    
    display_headers = headers
    display_rows = []
    for row in rows:
        full_row = list(row) + [""] * (num_cols - len(row))
        display_rows.append(full_row)

    col_widths = [get_display_width(str(h)) + 2 for h in display_headers]
    for row in display_rows:
        for i in range(num_cols):
            col_widths[i] = max(col_widths[i], get_display_width(str(row[i])) + 2)

    border_overhead = num_cols + 1
    
    is_truncated = False
    if max_width:
        total_width_with_borders = sum(col_widths) + border_overhead
        if total_width_with_borders > max_width:
            is_truncated = True
            
            available_for_content = max_width - border_overhead
            new_col_widths = [0] * num_cols
            remaining_width = available_for_content
            
            for i in range(num_cols):
                h_name = display_headers[i]
                if h_name in full_display_cols:
                    take = min(col_widths[i], remaining_width - (num_cols - 1 - i) * 4)
                    take = max(take, 4)
                    new_col_widths[i] = take
                    remaining_width -= take
            
            min_widths = []
            for i in range(num_cols):
                if new_col_widths[i] > 0:
                    min_widths.append(new_col_widths[i])
                    continue
                h_w = get_display_width(str(display_headers[i])) + 2
                min_widths.append(min(h_w, 10))
            
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
        
        return "\u2551" + "\u2551".join(parts) + "\u2551"

    top_border = "\u2554" + "\u2566".join(["\u2550" * w for w in col_widths]) + "\u2557"
    sep_border = "\u2560" + "\u256c".join(["\u2550" * w for w in col_widths]) + "\u2563"
    bottom_border = "\u255a" + "\u2569".join(["\u2550" * w for w in col_widths]) + "\u255d"

    formatted_lines = []
    formatted_lines.append(top_border)
    formatted_lines.append(get_data_line(display_headers, col_widths))
    formatted_lines.append(sep_border)
    for row in display_rows:
        formatted_lines.append(get_data_line(row, col_widths))
    formatted_lines.append(bottom_border)

    report_path = None
    if is_truncated:
        project_root = Path(__file__).resolve().parent.parent.parent
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
    project_root = Path(__file__).resolve().parent.parent.parent
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

def print_success_status(action_msg):
    """
    Unified success status reporting.
    Prints green bold 'Successfully' followed by action message.
    """
    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    GREEN = get_color("GREEN", "\033[32m")
    RESET = get_color("RESET", "\033[0m")
    
    parts = action_msg.split(" ", 1)
    if not parts:
        prefix = "Successfully"
        rest = ""
    else:
        prefix = f"Successfully {parts[0]}"
        rest = f" {parts[1]}" if len(parts) > 1 else ""
        
    print(f"\r\033[K{BOLD}{GREEN}{prefix}{RESET}{rest}", flush=True)
