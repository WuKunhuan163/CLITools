#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v11)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Supports timeout with auto-retry logic.
- Localized via 'translations.json'.
- Powered by standalone Python environment.
"""

import os
import sys
import warnings
import subprocess
import platform
import time
import random
import json
import argparse
import signal
from pathlib import Path

# Silence Tkinter deprecation warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

current_dir = Path(__file__).resolve().parent

try:
    from proj.tool_base import ToolBase
    from proj.gui_utils import setup_gui_environment, get_safe_python_for_gui, is_sandboxed
    from proj.language_utils import get_translation
except ImportError:
    # Fallback for manual execution or if PYTHONPATH is not set
    class ToolBase:
        def __init__(self, name):
            self.tool_name = name
            self.project_root = Path(__file__).resolve().parent.parent.parent
            self.script_dir = Path(__file__).resolve().parent
        def check_dependencies(self): return True
        def setup_gui(self): pass
    def setup_gui_environment(): pass
    def get_safe_python_for_gui(): return sys.executable
    def is_sandboxed(): return False
    def get_translation(d, k, default): return default

TOOL_PROJ_DIR = current_dir / "proj"

def _(key, default):
    return get_translation(str(TOOL_PROJ_DIR), key, default)

class UserInputRetryableError(Exception):
    """Exception raised for errors that should trigger a retry (e.g., user cancellation)."""
    pass

class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

    def get_python_exe(self, version="python3.10.19"):
        """Find a working python executable for GUI."""
        if os.environ.get("USERINPUT_DEBUG") == "1":
            print(f"DEBUG: Searching for python version: {version}")

        # 1. Try Tool's specific version
        python_exec = self.project_root / "tool" / "PYTHON" / "proj" / "install" / version / "install" / "bin" / "python3"
        if python_exec.exists():
            if os.environ.get("USERINPUT_DEBUG") == "1":
                print(f"DEBUG: Found tool python at: {python_exec}")
            return str(python_exec)

        # DO NOT FALLBACK TO SYSTEM PYTHON IF PYTHON TOOL IS MISSING
        print(f"\033[1;31m错误\033[0m: 工具 'PYTHON' ({version}) 未找到，无法启动 GUI。")
        print(f"请运行: TOOL install USERINPUT (它将自动安装 PYTHON 依赖)")
        sys.exit(1)

def get_python_exec(version="python3.10.19"):
    return UserInputTool().get_python_exe(version)

def get_project_name():
    """Retrieve the name of the current project."""
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        if git_root:
            return os.path.basename(git_root)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return os.path.basename(os.getcwd()) or "root"

def get_cursor_session_title(custom_id=None):
    project_name = get_project_name()
    base_title = f"{project_name} - Agent Mode"
    return f"{base_title} [{custom_id}]" if custom_id else base_title

def parse_gui_error(error_output):
    """Parse raw stderr output from the GUI process and return a human-readable message."""
    if not error_output:
        return "Unknown error (empty output)"
        
    if "Connection invalid" in error_output or "hiservices-xpcservice" in error_output:
        return _("err_sandbox", "Likely due to sandbox restrictions.")
    
    if "NSInternalInconsistencyException" in error_output or "aString != nil" in error_output:
        return _("err_sandbox", "Likely due to sandbox restrictions.")
        
    if "no display name" in error_output or "could not connect to display" in error_output:
        return _("err_no_display", "No display found. Cannot start GUI.")
    
    if "exited with code" in error_output:
        if "-6" in error_output or " 6" in error_output:
            return _("err_sandbox", "GUI crashed. Likely due to sandbox restrictions.")
        return _("err_sandbox", f"GUI process failed. {error_output}")
        
    if platform.system() == "Darwin":
        return _("err_sandbox", "GUI initialization failed. Likely due to sandbox restrictions.")

    lines = error_output.splitlines()
    return "\n".join(lines[:5]) + ("\n... (truncated)" if len(lines) > 5 else "")

def get_user_input_tkinter(title=None, timeout=180, hint_text=None):
    tool = UserInputTool()
    if not tool.check_dependencies():
        raise RuntimeError("Missing dependencies for USERINPUT")

    python_exe = tool.get_python_exe()
    proj_dir = str(tool.script_dir / "proj")
    
    # Python script template
    tkinter_script = r'''
import os
import sys
import json
import signal
import time
import threading
import subprocess
import platform
from pathlib import Path

# Try to import shared utils
PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists():
    sys.path.append(str(PROJECT_ROOT))

try:
    from proj.language_utils import get_translation
    from proj.gui_utils import setup_gui_environment
except ImportError:
    def get_translation(d, k, default): return default
    def setup_gui_environment(): pass

import tkinter as tk

TOOL_PROJ_DIR = %(proj_dir)r

def _(key, default):
    return get_translation(TOOL_PROJ_DIR, key, default)

class TkinterInputWindow:
    def __init__(self, title, timeout, hint_text):
        self.root = None
        self.text_widget = None
        self.title = title
        self.remaining_time = timeout
        self.hint_text = hint_text
        self.result = None
        self.window_closed = False

    def create_window(self):
        try:
            setup_gui_environment()
            prog_name = "USERINPUT"
            
            if platform.system() == "Darwin":
                self.root = tk.Tk(className=prog_name)
                try: self.root.tk.call('tk', 'appname', prog_name)
                except: pass
            else:
                self.root = tk.Tk()

            self.root.title(str(self.title))
            self.root.geometry("450x250")
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            
            main_frame = tk.Frame(self.root, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            tk.Label(main_frame, text=_("instruction", "Please enter your feedback:"), font=("Arial", 11), fg="#555").pack(pady=(0, 10), anchor='w')
            
            text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=8, font=("Arial", 12), bg="#f8f9fa", yscrollcommand=scrollbar.set)
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.text_widget.yview)
            if self.hint_text: self.text_widget.insert("1.0", self.hint_text)
            
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            tk.Button(button_frame, text=_("submit", "Submit"), command=self.submit_input, font=("Arial", 13, "bold")).pack(side=tk.RIGHT)
            tk.Button(button_frame, text=_("add_time", "Add 60s"), command=lambda: self.add_time(60), font=("Arial", 12)).pack(side=tk.RIGHT, padx=(0, 10))
            
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 12))
            self.status_label.pack(side=tk.LEFT)
            
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            self.text_widget.focus_set()
            self.start_timer()
            return True
        except Exception as e:
            print(f"ERROR: Tkinter init failed: {e}")
            return False

    def add_time(self, seconds):
        self.remaining_time += seconds

    def start_timer(self):
        def tick():
            while self.remaining_time > 0 and not self.window_closed:
                try: self.status_label.config(text=f"{_('time_remaining', 'Remaining:')} {self.remaining_time}s")
                except: break
                time.sleep(1)
                self.remaining_time -= 1
            if not self.window_closed: self.timeout_input()
        threading.Thread(target=tick, daemon=True).start()

    def submit_input(self):
        text = self.text_widget.get("1.0", tk.END).strip()
        self.result = {"status": "success", "data": text if text else "USER_SUBMITTED_EMPTY"}
        self.close()

    def cancel_input(self):
        self.result = {"status": "cancelled", "data": None}
        self.close()

    def timeout_input(self):
        text = self.text_widget.get("1.0", tk.END).strip()
        self.result = {"status": "timeout", "data": text if text else None}
        self.close()

    def close(self):
        self.window_closed = True
        try:
            if self.root: self.root.destroy()
        except: pass

    def run(self):
        if self.create_window():
            self.root.mainloop()
            print("GDS_USERINPUT_JSON:" + json.dumps(self.result or {"status": "error", "data": "No result"}))

if __name__ == "__main__":
    window = TkinterInputWindow(%(title)r, %(timeout)d, %(hint)r)
    window.run()
''' % {
        'project_root': str(tool.project_root),
        'proj_dir': proj_dir,
        'title': title,
        'timeout': timeout,
        'hint': hint_text
    }

    try:
        proc = subprocess.Popen(
            [python_exe, '-c', tkinter_script],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
        )
        stdout, stderr = proc.communicate(timeout=timeout + 30)
        
        if proc.returncode != 0:
            raise RuntimeError(parse_gui_error(stderr or stdout))

        for line in stdout.splitlines():
            if line.startswith("GDS_USERINPUT_JSON:"):
                res = json.loads(line[len("GDS_USERINPUT_JSON:"):])
                if res['status'] == 'success':
                    if res['data'] == 'USER_SUBMITTED_EMPTY':
                        raise UserInputRetryableError(_("msg_empty", "Empty content"))
                    return res['data']
                elif res['status'] == 'cancelled':
                    raise UserInputRetryableError(_("msg_cancelled", "Cancelled"))
                elif res['status'] == 'timeout':
                    if res['data']: return res['data']
                    raise UserInputRetryableError(_("msg_timeout", "Timeout"))
        
        raise RuntimeError("No valid response from GUI")
    except subprocess.TimeoutExpired:
        proc.kill()
        raise UserInputRetryableError(_("msg_timeout", "Timeout"))

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    args = parser.parse_args()

    max_retries = 3
    for attempt in range(max_retries):
        try:
            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint)
            
            end_hint = "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 指到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
            print(result + end_hint)
            
            if platform.system() == "Darwin":
                try: subprocess.run('pbcopy', input=result + end_hint, text=True, encoding='utf-8', check=True)
                except: pass
            return 0
        except (UserInputRetryableError, RuntimeError) as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt+1} failed: {e}. Retrying...", file=sys.stderr)
                time.sleep(1)
                continue
            print(f"Error: {e}", file=sys.stderr)
            return 1

if __name__ == "__main__":
    sys.exit(main())
