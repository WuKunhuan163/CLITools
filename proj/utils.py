import os
import sys
import re
import json
import unicodedata
import difflib
from pathlib import Path

def get_display_width(text):
    """
    Calculate the display width of a string, considering multi-byte characters
    and ignoring ANSI escape sequences and RTL markers.
    """
    # Strip ANSI escape sequences and RTL markers (\u202b, \u202c)
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])|[\u202b\u202c]')
    stripped_text = ansi_escape.sub('', text)
    
    width = 0
    for char in stripped_text:
        eaw = unicodedata.east_asian_width(char)
        if eaw in ('W', 'F'):
            width += 2
        else:
            width += 1
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

def format_table(headers, rows, max_width=None, save_dir="tmp", is_rtl=False, full_display_cols=None):
    """
    Formats a table with double-line box-drawing characters and optional truncation.
    If truncated, saves the full table to a Markdown file.
    full_display_cols: List of header names that should be prioritized for full display.
    """
    if not headers or not rows:
        return "", None

    num_cols = len(headers)
    full_display_cols = full_display_cols or []
    
    # If RTL, reverse columns for display
    display_headers = list(reversed(headers)) if is_rtl else headers
    display_rows = []
    for row in rows:
        full_row = list(row) + [""] * (num_cols - len(row))
        display_rows.append(list(reversed(full_row)) if is_rtl else full_row)

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
            # Re-adjust remaining_width if we were too aggressive in pass 1
            # But here we just proceed to distribution.
            
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
        
        line = "║" + "║".join(parts) + "║"
        if is_rtl:
            # Wrap in RTL markers to ensure correct display in RTL-capable terminals
            return f"\u202b{line}\u202c\x1B[0m"
        return line + "\x1B[0m"

    def wrap_rtl(line):
        if is_rtl:
            return f"\u202b{line}\u202c\x1B[0m"
        return line + "\x1B[0m"

    # Construct borders
    top_border = wrap_rtl("╔" + "╦".join(["═" * w for w in col_widths]) + "╗")
    sep_border = wrap_rtl("╠" + "╬".join(["═" * w for w in col_widths]) + "╣")
    bottom_border = wrap_rtl("╚" + "╩".join(["═" * w for w in col_widths]) + "╝")

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

def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """
    Returns a list of the best "good enough" matches.
    """
    return difflib.get_close_matches(word, possibilities, n=n, cutoff=cutoff)
