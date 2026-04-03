#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Uses interface.gui logic (same as FILEDIALOG) to spawn the UI safely.
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
        _tool_instance = UserInputTool()
    return _tool_instance.get_translation(key, default).format(**kwargs)

class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

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

def get_user_selection(title, timeout, hint_text, custom_id=None, tool=None):
    if tool is None:
        tool = UserInputTool()
    
    try:
        from interface.gui import get_safe_python_for_gui
        python_exe = get_safe_python_for_gui()
    except ImportError:
        python_exe = tool.get_python_exe()
    
    tkinter_script = r'''
import sys
import os
import time
import json
import traceback
import shlex
import re
import threading
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists() and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from interface.gui import BaseGUIWindow, setup_common_bottom_bar
    from interface.gui import setup_gui_environment
    from interface.gui import get_label_style, get_gui_colors, get_button_style
except ImportError as e:
    print("GDS_GUI_RESULT_JSON:{{\"status\": \"error\", \"message\": \"Failed to import blueprint: " + str(e) + "\"}}")
    sys.exit(1)

import tkinter as tk
TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT", focus_interval=focus_interval)
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.text_widget = None
        self._last_trigger_time = 0
        self.is_triggering_subtool = False

    def get_current_state(self):
        if self.text_widget: return self.text_widget.get("1.0", tk.END).strip()
        return None

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("450x250")
        
        self.status_label = setup_common_bottom_bar(
            self.root, self,
            submit_text="Submit",
            submit_cmd=lambda: self.finalize("success", self.get_current_state() or "USER_SUBMITTED_EMPTY"),
            add_time_increment=self.time_increment
        )
        
        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        font_style = get_label_style()
        tk.Label(main_frame, text="Please enter your feedback:", font=font_style, fg="#555").pack(pady=(0, 5), anchor='w')
        
        text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=7, font=font_style, bg="#f8f9fa", yscrollcommand=scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget.bind("<Key>", self.on_any_key)
        scrollbar.config(command=self.text_widget.yview)
        
        if self.hint_text: 
            self.text_widget.insert("1.0", self.hint_text)
            self.text_widget.focus_set()
            
        self.start_timer(self.status_label)

    def on_any_key(self, event):
        now = time.time()
        if now - self._last_trigger_time < 0.8: return

        is_shift_2 = (event.keysym == "2" and (event.state & 0x1))
        if event.char == "@" or event.keysym == "at" or is_shift_2:
            self._last_trigger_time = now
            self.root.after(10, self.run_file_dialog_trigger)

    def run_file_dialog_trigger(self):
        if self.is_triggering_subtool: return
        self.is_triggering_subtool = True
        
        def run_in_thread():
            try:
                try:
                    from tool.FILEDIALOG.logic.interface.main import get_file_dialog_bin
                    fd_bin = get_file_dialog_bin()
                except ImportError:
                    fd_bin = "FILEDIALOG"
                
                env = os.environ.copy()
                env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
                cmd = [sys.executable, str(PROJECT_ROOT / "bin" / "FILEDIALOG" / fd_bin), "--multiple", "--title", "Select Entities"]
                
                try:
                    res = subprocess.run(cmd, capture_output=True, text=True, env=env)
                except Exception as ex:
                    return
                
                if res.returncode == 0:
                    output = res.stdout.strip()
                    paths = []
                    for line in output.splitlines():
                        if line.startswith("Selected: "):
                            paths.append(line[len("Selected: "):].strip())
                        else:
                            match = re.match(r"^\s*\d+\.\s*(.*)$", line)
                            if match: paths.append(match.group(1).strip())
                    
                    if paths:
                        def insert_paths():
                            formatted_paths = []
                            for p in paths:
                                if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
                                    formatted_paths.append(f"@{p}")
                                else:
                                    q_p = shlex.quote(p) if " " in p else p
                                    formatted_paths.append(f"@{q_p}")
                            
                            cursor_pos = self.text_widget.index(tk.INSERT)
                            prev_char = self.text_widget.get(f"{cursor_pos}-1c", cursor_pos)
                            if prev_char == "@": self.text_widget.delete(f"{cursor_pos}-1c", cursor_pos)
                            
                            formatted = ", ".join(formatted_paths)
                            self.text_widget.insert(tk.INSERT, formatted)
                        
                        self.root.after(0, insert_paths)
            finally:
                self.is_triggering_subtool = False
                self._last_trigger_time = time.time()
                
        threading.Thread(target=run_in_thread, daemon=True).start()

if __name__ == "__main__":
    try:
        win = UserInputWindow(%(title)r, %(timeout)d, %(hint)r, 90, 60)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except Exception as e:
        print("GDS_GUI_RESULT_JSON:{{\"status\": \"error\", \"message\": \"" + str(e).replace('"', '\\"') + "\"}}")
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'title': title,
        'timeout': timeout,
        'hint': hint_text,
        'custom_id': custom_id
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        import subprocess
        import json
        env = os.environ.copy()
        env['GDS_GUI_MANAGED'] = '1'
        res = subprocess.run([python_exe, tmp_path], capture_output=True, text=True, env=env)
        
        for line in res.stdout.split('\n'):
            if line.startswith("GDS_GUI_RESULT_JSON:"):
                return json.loads(line[len("GDS_GUI_RESULT_JSON:"):])
        
        return {"status": "error", "message": f"No valid output. STDOUT: {res.stdout}\nSTDERR: {res.stderr}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def main():
    tool = UserInputTool()

    # Early intercept remote GUI control commands
    _gui_cmd_map = {"--gui-submit": "submit", "--gui-cancel": "cancel", "--gui-stop": "stop", "--gui-add-time": "add_time"}
    _gui_match = next((f for f in _gui_cmd_map if f in sys.argv), None)
    if _gui_match:
        try:
            from interface.gui import handle_gui_remote_command
            remaining = [a for a in sys.argv[1:] if a not in _gui_cmd_map and a != "--no-warning"]
            return handle_gui_remote_command("USERINPUT", tool.project_root, _gui_cmd_map[_gui_match], remaining, tool.get_translation)
        except ImportError:
            pass

    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    
    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()

    title = f"USERINPUT - {args.id}" if args.id else "USERINPUT"
    
    result = get_user_selection(title, args.timeout, args.hint, custom_id=args.id, tool=tool)
    
    BOLD, GREEN, RED, RESET = "\033[1m", "\033[32m", "\033[31m", "\033[0m"

    if result['status'] == 'success':
        data = result['data']
        print(f"{BOLD}{GREEN}Successfully received{RESET}:\n{data}")
        return 0
    elif result['status'] in ['cancelled', 'terminated']:
        print(f"{BOLD}{RED}Aborted{RESET}: {result['status'].capitalize()} - {result.get('reason', '')}")
        return 1
    elif result['status'] == 'timeout':
        print(f"{BOLD}{RED}Error{RESET}: Input Timeout")
        return 1
    else:
        err_msg = result.get('message', 'Unknown error')
        print(f"Error: {err_msg}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
