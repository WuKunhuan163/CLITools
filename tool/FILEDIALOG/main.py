#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FILEDIALOG Tool (v2)
- Advanced file and directory selection via custom Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Supports batch selection (Shift/Cmd/Ctrl) and remote kill/submit.
- Integrated with project's shared GUI logic and styling.
"""

import os
import sys
import json
import argparse
import platform
import subprocess
import threading
import time
import tempfile
from pathlib import Path
from typing import List, Tuple, Optional, Any

# Fix shadowing
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from logic.tool.base import ToolBase
    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
except ImportError:
    # Minimal fallback
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.project_root = Path(__file__).resolve().parent.parent.parent
            self.script_dir = Path(__file__).resolve().parent
        def handle_command_line(self): return False
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
            from tool.PYTHON.logic.config import INSTALL_DIR
            install_root = INSTALL_DIR
        except ImportError:
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

def get_user_selection(title, initial_dir, file_types, multiple, directory_only, custom_id=None):
    tool = FileDialogTool()
    python_exe = tool.get_python_exe()
    
    tkinter_script = r'''
import os
import sys
import json
import tkinter as tk
from tkinter import ttk
from pathlib import Path

PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists() and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from logic.gui.base import BaseGUIWindow, setup_common_bottom_bar
    from logic.gui.engine import setup_gui_environment
    from logic.gui.style import get_label_style, get_gui_colors, get_button_style
except ImportError:
    sys.exit("Error: Could not import logic.gui.base")

TOOL_INTERNAL = %(internal_dir)r

class FileDialogWindow(BaseGUIWindow):
    def __init__(self, title, timeout, initial_dir, file_types, multiple, directory_only):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="FILEDIALOG")
        self.current_dir = Path(initial_dir).expanduser().resolve()
        if not self.current_dir.is_dir():
            self.current_dir = Path.home()
        self.file_types = file_types
        self.multiple = multiple
        self.directory_only = directory_only
        self.tree = None
        self.path_var = None

    def get_current_state(self):
        if not self.tree: return None
        selected = self.tree.selection()
        if not selected: return None
        
        paths = []
        for item in selected:
            # item is usually the absolute path string we used as ID
            paths.append(item)
        
        if self.multiple: return paths
        return paths[0] if paths else None

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("600x450")
        
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text=self._("btn_select", "Select"),
            submit_cmd=lambda: self.finalize("success", self.get_current_state()),
            add_time_increment=60 # Enable add time for file dialog
        )

        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Path navigation bar
        nav_frame = tk.Frame(main_frame)
        nav_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Button(nav_frame, text="▲", command=self.go_up, font=get_button_style()).pack(side=tk.LEFT, padx=(0, 5))
        
        self.path_var = tk.StringVar(value=str(self.current_dir))
        path_entry = tk.Entry(nav_frame, textvariable=self.path_var, font=get_label_style())
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        path_entry.bind("<Return>", lambda e: self.go_to_path())

        # File list with Treeview
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(tree_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        columns = ("name", "size", "type")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings", 
                                  selectmode="extended" if self.multiple else "browse",
                                  yscrollcommand=scrollbar.set)
        
        self.tree.heading("name", text=self._("col_name", "Name"))
        self.tree.heading("size", text=self._("col_size", "Size"))
        self.tree.heading("type", text=self._("col_type", "Type"))
        
        self.tree.column("name", width=350)
        self.tree.column("size", width=100, anchor="e")
        self.tree.column("type", width=100)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<Double-1>", self.on_double_click)
        self.refresh_list()
        
        self.start_timer(self.status_label)

    def refresh_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        try:
            items = sorted(list(self.current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name.lower()))
            for item in items:
                if self.directory_only and not item.is_dir():
                    continue
                
                # Simple extension check if not all
                if not self.directory_only and not item.is_dir():
                    if not self.match_file_types(item):
                        continue
                
                name = item.name + ("/" if item.is_dir() else "")
                size = "" if item.is_dir() else self.format_size(item.stat().st_size)
                itype = self._("type_folder", "Folder") if item.is_dir() else self._("type_file", "File")
                
                self.tree.insert("", tk.END, iid=str(item), values=(name, size, itype))
        except Exception as e:
            self.tree.insert("", tk.END, values=(f"Error: {e}", "", ""))

    def match_file_types(self, path):
        # file_types is like [('PDF files', '*.pdf'), ...]
        if not self.file_types or any(t[1] == '*.*' for t in self.file_types):
            return True
        
        ext = path.suffix.lower()
        for label, pattern in self.file_types:
            patterns = pattern.split()
            for p in patterns:
                if p.startswith("*.") and ext == p[1:]:
                    return True
                elif p == ext:
                    return True
        return False

    def format_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def go_up(self):
        self.current_dir = self.current_dir.parent
        self.path_var.set(str(self.current_dir))
        self.refresh_list()

    def go_to_path(self):
        p = Path(self.path_var.get()).expanduser().resolve()
        if p.is_dir():
            self.current_dir = p
            self.refresh_list()

    def on_double_click(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id: return
        
        path = Path(item_id)
        if path.is_dir():
            self.current_dir = path
            self.path_var.set(str(self.current_dir))
            self.refresh_list()

if __name__ == "__main__":
    try:
        win = FileDialogWindow(%(title)r, 300, %(initial_dir)r, %(file_types)r, %(multiple)r, %(directory_only)r)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except Exception as e:
        import traceback
        traceback.print_exc()
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
        res = tool.run_gui(python_exe, tmp_path, 300, custom_id)
        return res
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def main():
    tool = FileDialogTool()
    if tool.handle_command_line():
        return 0

    parser = argparse.ArgumentParser(description="FILEDIALOG Tool")
    parser.add_argument('command', nargs='?', help="Command to run (stop, submit, cancel)")
    parser.add_argument('--types', type=str, default="all")
    parser.add_argument('--title', type=str, default="Select File")
    parser.add_argument('--dir', type=str)
    parser.add_argument('--multiple', action='store_true')
    parser.add_argument('--directory', action='store_true')
    parser.add_argument('--id', type=str)
    
    args, unknown = parser.parse_known_args()
    
    # Standard remote commands
    if args.command in ["stop", "submit", "cancel", "add_time"]:
        from logic.gui.manager import handle_gui_remote_command
        return handle_gui_remote_command("FILEDIALOG", tool.project_root, args.command, unknown, tool.get_translation)

    initial_dir = args.dir or os.getcwd()
    file_types = parse_file_types(args.types)
    
    result = get_user_selection(args.title, initial_dir, file_types, args.multiple, args.directory, custom_id=args.id)
    
    from logic.config import get_color
    BOLD, GREEN, RED, RESET = get_color("BOLD", "\033[1m"), get_color("GREEN", "\033[32m"), get_color("RED", "\033[31m"), get_color("RESET", "\033[0m")

    if result['status'] == 'success':
        selected_label = get_msg("label_filedialog_selected", "Selected")
        data = result['data']
        if isinstance(data, list):
            print(f"{BOLD}{GREEN}{selected_label}{RESET} ({len(data)}):")
            for i, p in enumerate(data, 1):
                print(f"  {i}. {p}")
        else:
            print(f"{BOLD}{GREEN}{selected_label}{RESET}: {data}")
        return 0
    elif result['status'] in ['cancelled', 'terminated']:
        label = get_msg('label_terminated', 'Terminated')
        if result['status'] == 'cancelled':
            msg = get_msg('msg_cancelled', 'Cancelled')
        else:
            reason = result.get('reason', 'stop')
            reason_map = {
                "stop": get_msg("msg_terminated_external", "Instance terminated from external signal"),
                "interrupted": get_msg("msg_interrupted", "Interrupted by user"),
                "signal": get_msg("msg_terminated_external", "Instance terminated from external signal")
            }
            msg = reason_map.get(reason, reason)
        print(f"{BOLD}{RED}{label}{RESET}: {msg}")
        return 1
    elif result['status'] == 'timeout':
        label = get_msg('label_error', 'Error')
        msg = get_msg('msg_timeout', 'Input Timeout')
        print(f"{BOLD}{RED}{label}{RESET}: {msg}")
        return 1
    else:
        print(f"Error: {result.get('message', 'Unknown error')}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
