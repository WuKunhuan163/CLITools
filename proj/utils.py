import os
import sys
import re
import json
import unicodedata
import difflib
import builtins
from pathlib import Path

# Global state for RTL mode
_GLOBAL_RTL_MODE = False
_original_print = builtins.print

def _init_rtl_mode():
    """Initializes RTL mode based on environment or configuration."""
    global _GLOBAL_RTL_MODE
    current_lang = os.environ.get("TOOL_LANGUAGE")
    if not current_lang:
        try:
            # proj/utils.py is in proj/
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent
            config_path = project_root / "data" / "config.json"
            
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
        for char in line:
            res += mirror_map.get(char, char)
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

class AuditManager:
    """
    Manages audit/cache files for various components.
    Unified logic for caching and warning users.
    """
    def __init__(self, audit_dir, component_name=None):
        self.audit_dir = Path(audit_dir)
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.component_name = component_name

    def get_path(self, name):
        if not name.endswith(".json"):
            name = f"{name}.json"
        return self.audit_dir / name

    def load(self, name):
        path = self.get_path(name)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def save(self, name, data):
        path = self.get_path(name)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    def print_cache_warning(self):
        """Prints a standardized warning when cache is used."""
        BOLD = "\033[1m"
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        
        # We try to use translations if available via the component's _()
        warning_label = f"{BOLD}{YELLOW}Warning{RESET}"
        msg = "Using cached data. To force refresh, clear the audit/cache directory."
        
        # If we are in a tool context, we might have access to its translations
        # For now, print a generic but correctly formatted message
        print(f"{warning_label}: {msg}")
        if self.component_name:
            print(f"  Cache location: {self.audit_dir}")
