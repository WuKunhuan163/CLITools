#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FILEDIALOG Tool (v3)
- Advanced file and directory selection via custom Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Supports batch selection (Shift/Cmd/Ctrl) and remote kill/submit.
- Integrated with project's shared GUI logic and styling.
- ENHANCED: Added Staging Area (shopping cart) with resizable PanedWindow.
- ENHANCED: Results combine currently selected items + staged items.
"""

import os
import sys
import argparse
import platform
import tempfile
from pathlib import Path

# Fix shadowing
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from interface.tool import ToolBase
    from interface.gui import setup_gui_environment, get_safe_python_for_gui
    from interface.lang import get_translation
    from interface.utils import get_logic_dir
except ImportError:
    # Minimal fallback
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.project_root = Path(__file__).resolve().parent.parent.parent
            self.script_dir = Path(__file__).resolve().parent
        def handle_command_line(self, parser): return False
    def get_translation(d, k, default): return default
    def get_logic_dir(d): return d / "logic"

current_dir = Path(__file__).resolve().parent
TOOL_INTERNAL = current_dir / "logic"

def get_msg(key, default, **kwargs):
    global _tool_instance
    if '_tool_instance' not in globals():
        _tool_instance = FileDialogTool()
    return _tool_instance.get_translation(key, default).format(**kwargs)

class FileDialogTool(ToolBase):
    def __init__(self):
        super().__init__("FILEDIALOG")

    def get_python_exe(self, version=None):
        if not version: version = "3.11.14"
        try:
            from interface import get_interface
            python_iface = get_interface("PYTHON")
            install_root = python_iface.get_python_install_dir()
        except (ImportError, AttributeError):
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

        system_tag = "macos"
        machine = platform.machine().lower()
        if sys.platform == "darwin":
            system_tag = "macos-arm64" if "arm" in machine or "aarch64" in machine else "macos"
        elif sys.platform == "linux": system_tag = "linux64"
        elif sys.platform == "win32": system_tag = "windows-amd64"

        v = version[7:] if version.startswith("python3") else (version[6:] if version.startswith("python") else version)
        possible_dirs = [v, f"{v}-{system_tag}", f"python{v}-{system_tag}", f"python3{v}-{system_tag}"]
        
        for d in possible_dirs:
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)
        return sys.executable

    def get_ai_instruction(self):
        return get_msg("ai_instruction", "Use FILEDIALOG to let users select local files or directories for processing. You can specify file types (e.g., pdf, image) and initial directories. Supports batch selection via Shift/Cmd/Ctrl.")

    def get_fallback_initial_content(self, hint):
        """Custom hint for FILEDIALOG file fallback."""
        return hint or get_msg("fallback_filedialog_hint", "Please enter the absolute paths of files/directories you want to select, one per line:")

    def process_fallback_result(self, content):
        """Parse fallback file content as a list of paths, ignoring the initial hint."""
        hint = self.get_fallback_initial_content(None).strip()
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        
        # Filter out the hint line if it's there
        paths = [l for l in lines if l != hint]
        
        if not paths: return None
        return paths

def parse_file_types(file_types_str: str):
    if not file_types_str or file_types_str.lower() == "all":
        return [('All files', '*.*')]
    
    predefined = {
        'pdf': ('PDF files', '*.pdf'),
        'txt': ('Text files', '*.txt'),
        'doc': ('Word documents', '*.doc *.docx'),
        'image': ('Image files', '*.png *.jpg *.jpeg *.gif *.bmp *.tiff'),
        'py': ('Python files', '*.py'),
        'json': ('JSON files', '*.json'),
        'zip': ('Archive files', '*.zip *.rar *.7z *.tar *.gz'),
        'all': ('All files', '*.*')
    }
    
    types = []
    for t in file_types_str.split(','):
        t = t.strip().lower()
        if t in predefined:
            types.append(predefined[t])
        elif t.startswith('*.'):
            types.append((f"{t[2:].upper()} files", t))
        else:
            types.append((f"{t.upper()} files", f"*.{t}"))
            
    if ('All files', '*.*') not in types:
        types.append(('All files', '*.*'))
    return types

def get_user_selection(title, initial_dir, file_types, multiple, directory_only, custom_id=None, tool=None):
    if tool is None:
        tool = FileDialogTool()
        # Initialize quiet mode if needed
        tool.is_quiet = "--tool-quiet" in sys.argv
    
    from interface.gui import get_safe_python_for_gui
    python_exe = get_safe_python_for_gui()
    
    tkinter_script = r'''
import os
import sys
import json
import tkinter as tk
import platform
import tkinter.font as tkFont
from tkinter import ttk
from pathlib import Path

PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists() and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from interface.gui import BaseGUIWindow, setup_common_bottom_bar
    from interface.gui import setup_gui_environment
    from interface.gui import get_label_style, get_gui_colors, get_button_style
except ImportError:
    sys.exit("Error: Could not import GUI blueprint components")

TOOL_INTERNAL = %(internal_dir)r

class FileDialogWindow(BaseGUIWindow):
    def __init__(self, title, timeout, initial_dir, file_types, multiple, directory_only):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="FILEDIALOG", focus_interval=90)
        self.current_dir = Path(initial_dir).expanduser().resolve()
        if not self.current_dir.is_dir():
            self.current_dir = Path.home()
        self.file_types = file_types
        self.multiple = multiple
        self.directory_only = directory_only
        self.tree = None
        self.staging_tree = None
        self.staged_items = set()
        self.breadcrumb_frame = None
        self.history = [self.current_dir]
        self.history_index = 0
        self.back_btn = None
        self.forward_btn = None
        self.sort_column = "name"
        self.sort_reverse = False
        self.last_selected = None
        self._updating_breadcrumbs = False

    def get_current_state(self):
        if not self.tree: return None
        
        # Combine staged items and current selection
        final_paths = list(self.staged_items)
        
        selected = self.tree.selection()
        for item in selected:
            if item not in self.staged_items:
                final_paths.append(item)
        
        if not final_paths: return None
        
        if self.multiple: return final_paths
        return final_paths[0] if final_paths else None

    def on_submit(self):
        state = self.get_current_state()
        if state:
            if isinstance(state, list):
                # Copy as a list (one per line)
                self.copy_to_clipboard("\n".join(state))
            else:
                self.copy_to_clipboard(str(state))
        self.finalize("success", state)

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
        except: pass

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("900x550") # Wider for staging area
        
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text=self._("btn_select", "Select"),
            submit_cmd=self.on_submit,
            add_time_increment=60 
        )

        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Path navigation bar
        nav_frame = tk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        # History buttons
        self.back_btn = tk.Button(nav_frame, text="←", command=self.go_back, font=get_button_style())
        self.back_btn.pack(side=tk.LEFT, padx=(0, 2))
        
        self.forward_btn = tk.Button(nav_frame, text="→", command=self.go_forward, font=get_button_style())
        self.forward_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.update_history_buttons()

        # Breadcrumb frame
        self.breadcrumb_frame = tk.Frame(nav_frame, bg="white", relief=tk.SUNKEN, borderwidth=1)
        self.breadcrumb_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.breadcrumb_frame.bind("<Configure>", self.on_breadcrumb_configure)
        
        # Initial render after delay
        self.root.after(100, self.update_breadcrumbs)

        # PanedWindow for resizable split
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left side: File Browser
        browser_container = tk.Frame(paned)
        paned.add(browser_container, weight=60)

        # File list with Treeview
        tree_frame = tk.Frame(browser_container)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("name", "size", "type")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                                  selectmode="extended" if self.multiple else "browse",
                                  yscrollcommand=scrollbar.set)
        
        for col in columns:
            self.tree.heading(col, text=self._(f"col_{col}", col.capitalize()), 
                              command=lambda c=col: self.on_header_click(c))
        
        self.tree.column("name", width=250)
        self.tree.column("size", width=80, anchor="e")
        self.tree.column("type", width=80)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<Button-1>", self.on_click)
        self.tree.bind("<Shift-Button-1>", self.on_shift_click)
        self.tree.bind("<Control-Button-1>", self.on_ctrl_click)
        if platform.system() == "Darwin":
            self.tree.bind("<Command-Button-1>", self.on_ctrl_click)

        # Staging Area Buttons
        stage_btn_frame = tk.Frame(browser_container)
        stage_btn_frame.pack(fill=tk.X, pady=5)
        
        add_to_stage_btn = tk.Button(stage_btn_frame, text=self._("btn_add_to_staging", "Add to Staging"), 
                                     command=self.add_selected_to_staging, font=get_button_style())
        add_to_stage_btn.pack(side=tk.RIGHT)

        # Right side: Staging Area
        staging_container = tk.Frame(paned)
        paned.add(staging_container, weight=40)

        tk.Label(staging_container, text=self._("label_staging_area", "Staging Area"), font=get_label_style()).pack(anchor="w")
        
        staging_frame = tk.Frame(staging_container)
        staging_frame.pack(fill=tk.BOTH, expand=True)
        
        s_scrollbar = tk.Scrollbar(staging_frame)
        s_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.staging_tree = ttk.Treeview(staging_frame, columns=("path",), show="headings",
                                         selectmode="extended", yscrollcommand=s_scrollbar.set)
        self.staging_tree.heading("path", text=self._("col_path", "Staged Path"))
        self.staging_tree.column("path", width=200)
        self.staging_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        s_scrollbar.config(command=self.staging_tree.yview)
        
        # Remove from staging logic
        remove_from_stage_btn = tk.Button(staging_container, text=self._("btn_remove_from_staging", "Remove Selected"), 
                                          command=self.remove_selected_from_staging, font=get_button_style())
        remove_from_stage_btn.pack(side=tk.RIGHT, pady=5)

        self.refresh_list()
        self.update_header_text()
        
        self.start_timer(self.status_label)
        
        # Force topmost with multiple attempts and a small delay to override parent windows (Interface I focus priority)
        def force_focus(attempt=0):
            if not self.window_closed and self.root:
                self.root.lift()
                self.root.attributes("-topmost", True)
                self.root.focus_force()
                if attempt < 5: # Try a few times to win against other topmost windows
                    self.root.after(100, lambda: force_focus(attempt + 1))
        self.root.after(150, force_focus)

    def add_selected_to_staging(self):
        selected = self.tree.selection()
        for item in selected:
            if item not in self.staged_items:
                self.staged_items.add(item)
                self.staging_tree.insert("", tk.END, iid=item, values=(item,))
        self.update_staging_count()

    def remove_selected_from_staging(self):
        selected = self.staging_tree.selection()
        for item in selected:
            if item in self.staged_items:
                self.staged_items.remove(item)
                self.staging_tree.delete(item)
        self.update_staging_count()

    def update_staging_count(self):
        count = len(self.staged_items)
        if hasattr(self, "status_label"):
            # Update status message temporarily
            # rem_msg = self._('time_remaining', 'Remaining:')
            # self.status_label.config(text=f"Staged: {count} items | {rem_msg} {self.remaining_time}s")
            pass

    def on_breadcrumb_configure(self, event):
        if hasattr(self, "_breadcrumb_timer"):
            self.root.after_cancel(self._breadcrumb_timer)
        self._breadcrumb_timer = self.root.after(50, self.update_breadcrumbs)

    def update_breadcrumbs(self):
        if self._updating_breadcrumbs: return
        self._updating_breadcrumbs = True
        
        try:
            for widget in self.breadcrumb_frame.winfo_children():
                widget.destroy()
            
            path = self.current_dir
            parts = []
            while True:
                parts.append(path)
                if path.parent == path: break
                path = path.parent
            parts.reverse()

            blue_color = get_gui_colors().get("blue", "#007AFF")
            text_color = get_gui_colors().get("text", "#333333")
            font_style = get_label_style()
            measure_font = tkFont.Font(family=font_style[0], size=font_style[1])
            
            def get_name(part, index):
                if index == 0:
                    if platform.system() == "Darwin": return self._("label_macintosh_hd", "Macintosh HD")
                    elif platform.system() == "Windows": return self._("label_local_disk", "Local Disk")
                    else: return self._("label_file_system", "File System")
                return part.name

            self.root.update_idletasks()
            max_w = self.breadcrumb_frame.winfo_width()
            if max_w <= 1:
                self.root.after(50, self.update_breadcrumbs)
                return
            max_w -= 35

            sep_w = measure_font.measure(" / ")
            ellipsis_w = measure_font.measure("...")
            
            names = [get_name(p, i) for i, p in enumerate(parts)]
            full_w = sum(measure_font.measure(n) for n in names) + (len(names) - 1) * sep_w
                
            if full_w <= max_w:
                display_items = [(parts[i], i) for i in range(len(parts))]
            else:
                first_name = names[0]
                last_name = names[-1]
                current_w = measure_font.measure(first_name) + sep_w + ellipsis_w + sep_w + measure_font.measure(last_name)
                added_indices = []
                for i in range(len(parts) - 2, 0, -1):
                    w = measure_font.measure(names[i]) + sep_w
                    if current_w + w < max_w:
                        added_indices.insert(0, i)
                        current_w += w
                    else:
                        break
                
                display_items = [(parts[0], 0), ("...", -1)]
                for idx in added_indices:
                    display_items.append((parts[idx], idx))
                display_items.append((parts[-1], len(parts)-1))

            for i, (p, idx) in enumerate(display_items):
                is_last = (i == len(display_items) - 1)
                if p == "...":
                    lbl = tk.Label(self.breadcrumb_frame, text="...", bg="white", font=font_style)
                else:
                    name = get_name(p, idx)
                    if is_last:
                        lbl = tk.Label(self.breadcrumb_frame, text=name, fg=text_color, bg="white", font=font_style)
                    else:
                        lbl = tk.Label(self.breadcrumb_frame, text=name, fg=blue_color, cursor="hand2", bg="white", font=font_style)
                        lbl.bind("<Button-1>", lambda e, path=p: self.jump_to(path))
                
                lbl.pack(side=tk.LEFT)
                if i < len(display_items) - 1:
                    sep = tk.Label(self.breadcrumb_frame, text=" / ", bg="white", font=font_style)
                    sep.pack(side=tk.LEFT)
        finally:
            self._updating_breadcrumbs = False

    def update_history_buttons(self):
        if self.back_btn:
            self.back_btn.config(state=tk.NORMAL if self.history_index > 0 else tk.DISABLED)
        if self.forward_btn:
            self.forward_btn.config(state=tk.NORMAL if self.history_index < len(self.history) - 1 else tk.DISABLED)

    def jump_to(self, path):
        if path == self.current_dir: return
        self.history = self.history[:self.history_index + 1]
        self.history.append(path)
        self.history_index += 1
        self.current_dir = path
        self.refresh_list()
        self.update_breadcrumbs()
        self.update_history_buttons()

    def go_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.current_dir = self.history[self.history_index]
            self.refresh_list()
            self.update_breadcrumbs()
            self.update_history_buttons()

    def go_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.current_dir = self.history[self.history_index]
            self.refresh_list()
            self.update_breadcrumbs()
            self.update_history_buttons()

    def on_click(self, event):
        item = self.tree.identify_row(event.y)
        if item: self.last_selected = item

    def on_ctrl_click(self, event):
        item = self.tree.identify_row(event.y)
        if item: self.last_selected = item

    def on_shift_click(self, event):
        if not self.multiple: return
        item = self.tree.identify_row(event.y)
        if item and self.last_selected:
            all_items = self.tree.get_children()
            try:
                idx1 = all_items.index(self.last_selected)
                idx2 = all_items.index(item)
                start, end = min(idx1, idx2), max(idx1, idx2)
                range_items = all_items[start:end+1]
                current_selection = list(self.tree.selection())
                for ri in range_items:
                    if ri not in current_selection: current_selection.append(ri)
                self.tree.selection_set(current_selection)
                return "break"
            except ValueError: pass

    def on_header_click(self, column):
        if self.sort_column == column: self.sort_reverse = not self.sort_reverse
        else: self.sort_column, self.sort_reverse = column, False
        self.refresh_list(); self.update_header_text()

    def update_header_text(self):
        for col in ("name", "size", "type"):
            base_text = self._(f"col_{col}", col.capitalize())
            if col == self.sort_column:
                self.tree.heading(col, text=base_text + (" ↑" if self.sort_reverse else " ↓"))
            else: self.tree.heading(col, text=base_text)

    def refresh_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        try:
            try: raw_items = list(self.current_dir.iterdir())
            except: self.tree.insert("", tk.END, values=(self._("err_access_denied", "Access Denied"), "", "")); return
            if self.current_dir.parent != self.current_dir:
                self.tree.insert("", tk.END, iid="..", values=("..", "", self._("type_folder", "Folder")))
            
            def get_sort_val(item):
                is_dir = item.is_dir()
                if self.sort_column == "name": return item.name.lower()
                if self.sort_column == "size":
                    if is_dir: return -1
                    try: return item.stat().st_size
                    except: return 0
                if self.sort_column == "type": return (self._("type_folder", "Folder") if is_dir else self._("type_file", "File")).lower()
                return item.name.lower()
            
            items = sorted(raw_items, key=get_sort_val, reverse=self.sort_reverse)
            for item in items:
                try:
                    is_dir = item.is_dir()
                    if self.directory_only and not is_dir: continue
                    if not self.directory_only and not is_dir and not self.match_file_types(item): continue
                    name = item.name + ("/" if is_dir else "")
                    try: size = "" if is_dir else self.format_size(item.stat().st_size)
                    except: size = "???"
                    itype = self._("type_folder", "Folder") if is_dir else self._("type_file", "File")
                    self.tree.insert("", tk.END, iid=str(item), values=(name, size, itype))
                except: continue
        except Exception as e: self.tree.insert("", tk.END, values=(f"Error: {e}", "", ""))

    def match_file_types(self, path):
        if not self.file_types or any(t[1] == '*.*' for t in self.file_types): return True
        ext = path.suffix.lower()
        for label, pattern in self.file_types:
            for p in pattern.split():
                if (p.startswith("*.") and ext == p[1:]) or p == ext: return True
        return False

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0: return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def go_up(self): self.jump_to(self.current_dir.parent)

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        if item_id == "..": self.go_up(); return
        path = Path(item_id)
        if path.is_dir(): self.jump_to(path)

if __name__ == "__main__":
    try:
        win = FileDialogWindow(%(title)r, 300, %(initial_dir)r, %(file_types)r, %(multiple)r, %(directory_only)r)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except: import traceback; traceback.print_exc()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'title': title,
        'initial_dir': str(initial_dir),
        'file_types': file_types,
        'multiple': multiple,
        'directory_only': directory_only,
        'custom_id': custom_id
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='FILEDIALOG_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, 300, custom_id)
        if res.get("status") == "success" and isinstance(res.get("data"), list):
            if not multiple: res["data"] = res["data"][0]
        return res
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def main():
    tool = FileDialogTool()

    # Early intercept remote GUI control commands (--gui-submit, --gui-cancel, --gui-stop, --gui-add-time)
    _gui_cmd_map = {"--gui-submit": "submit", "--gui-cancel": "cancel", "--gui-stop": "stop", "--gui-add-time": "add_time"}
    _gui_match = next((f for f in _gui_cmd_map if f in sys.argv), None)
    if _gui_match:
        from interface.gui import handle_gui_remote_command
        remaining = [a for a in sys.argv[1:] if a not in _gui_cmd_map and a != "--no-warning"]
        return handle_gui_remote_command("FILEDIALOG", tool.project_root, _gui_cmd_map[_gui_match], remaining, tool.get_translation)

    parser = argparse.ArgumentParser(description="FILEDIALOG Tool")
    parser.add_argument('command', nargs='?', help="Command to run")
    parser.add_argument('--types', type=str, default="all")
    parser.add_argument('--title', type=str, default="Select File")
    parser.add_argument('--dir', type=str)
    parser.add_argument('--multiple', action='store_true')
    parser.add_argument('--directory', action='store_true')
    parser.add_argument('--id', type=str)
    
    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()

    initial_dir = args.dir or os.getcwd()
    file_types = parse_file_types(args.types)
    
    result = get_user_selection(args.title, initial_dir, file_types, args.multiple, args.directory, custom_id=args.id, tool=tool)
    
    from interface.config import get_color
    BOLD, GREEN, RED, RESET = get_color("BOLD", "\033[1m"), get_color("GREEN", "\033[32m"), get_color("RED", "\033[31m"), get_color("RESET", "\033[0m")

    if result['status'] == 'success':
        selected_label = get_msg("label_filedialog_selected", "Selected")
        data = result['data']
        import shlex
        if isinstance(data, list):
            output = f"({len(data)}):\n" + "\n".join([f"  {i}. {shlex.quote(p) if p and ' ' in p else (p or '')}" for i, p in enumerate(data, 1)])
            print(f"{BOLD}{GREEN}{selected_label}{RESET} {output}")
            tool.print_result_if_quiet(0, stdout="\n".join(data))
        else:
            display_data = shlex.quote(data) if data and " " in data else (data or "")
            print(f"{BOLD}{GREEN}{selected_label}{RESET}: {display_data}")
            tool.print_result_if_quiet(0, stdout=str(data))
        return 0
    elif result['status'] in ['cancelled', 'terminated']:
        label = get_msg('label_terminated', 'Terminated')
        if result['status'] == 'cancelled': msg = get_msg('msg_cancelled', 'Cancelled')
        else:
            reason = result.get('reason', 'stop')
            reason_map = {"stop": get_msg("msg_terminated_external", "Instance terminated from external signal"), "interrupted": get_msg("msg_interrupted", "Interrupted by user"), "signal": get_msg("msg_terminated_external", "Instance terminated from external signal")}
            msg = reason_map.get(reason, reason)
        print(f"{BOLD}{RED}{label}{RESET}: {msg}")
        tool.print_result_if_quiet(1, stderr=msg)
        return 1
    elif result['status'] == 'timeout':
        label, msg = get_msg('label_error', 'Error'), get_msg('msg_timeout', 'Input Timeout')
        print(f"{BOLD}{RED}{label}{RESET}: {msg}")
        tool.print_result_if_quiet(1, stderr=msg)
        return 1
    else:
        err_msg = result.get('message', 'Unknown error')
        print(f"Error: {err_msg}", file=sys.stderr)
        tool.print_result_if_quiet(1, stderr=err_msg)
        return 1

if __name__ == "__main__":
    sys.exit(main())
