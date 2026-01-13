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
    and ignoring ANSI escape sequences.
    """
    # Strip ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
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
    and ANSI escape sequences into account.
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

def format_table(headers, rows, max_width=None, save_dir="tmp", is_rtl=False):
    """
    Formats a table with alignment and optional truncation.
    If truncated, saves the full table to a Markdown file.
    """
    if not headers or not rows:
        return "", None

    num_cols = len(headers)
    col_widths = [get_display_width(h) for h in headers]
    for row in rows:
        for i in range(min(num_cols, len(row))):
            col_widths[i] = max(col_widths[i], get_display_width(str(row[i])))

    col_widths = [w + 2 for w in col_widths]
    
    total_width = sum(col_widths)
    is_truncated = False
    if max_width and total_width > max_width:
        is_truncated = True
    
    def get_line(data_row, widths, truncate=False):
        parts = []
        if is_rtl:
            ordered_data = list(reversed(data_row))
            ordered_widths = list(reversed(widths))
        else:
            ordered_data = data_row
            ordered_widths = widths

        current_total = 0
        for i, val in enumerate(ordered_data):
            val_str = str(val)
            w = ordered_widths[i]
            
            if truncate and current_total + w > max_width:
                available = max_width - current_total
                if available > 3:
                    val_str = truncate_to_display_width(val_str, available - 3) + "..."
                    parts.append(f"{val_str:<{available}}")
                elif available > 0:
                    val_str = truncate_to_display_width(val_str, available)
                    parts.append(f"{val_str:<{available}}")
                break
            
            padding = " " * (w - get_display_width(val_str))
            parts.append(f"{val_str}{padding}")
            current_total += w
            
        line = "".join(parts)
        if is_rtl:
            return f"\u202b{line}\u202c\x1B[0m"
        return line + "\x1B[0m"

    formatted_lines = []
    formatted_lines.append(get_line(headers, col_widths, is_truncated))
    
    table_real_width = min(total_width, max_width) if max_width else total_width
    formatted_lines.append("-" * table_real_width)
    
    for row in rows:
        formatted_lines.append(get_line(row, col_widths, is_truncated))

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
        except Exception:
            pass

    return "\n".join(formatted_lines), report_path

def get_close_matches(word, possibilities, n=3, cutoff=0.6):
    """
    Returns a list of the best "good enough" matches.
    """
    return difflib.get_close_matches(word, possibilities, n=n, cutoff=cutoff)
