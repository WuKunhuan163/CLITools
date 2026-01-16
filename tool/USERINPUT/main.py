#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v16)
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
import traceback
import threading
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
        def handle_command_line(self):
            if len(sys.argv) > 1 and sys.argv[1] == "setup":
                setup_script = self.script_dir / "setup.py"
                if setup_script.exists():
                    subprocess.run([sys.executable, str(setup_script)] + sys.argv[2:])
                    sys.exit(0)
            return False
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

    def get_python_exe(self, version=None):
        """Find a working python executable for GUI."""
        if not version:
            config = get_config()
            version = config.get("python_version", "python3.11.14")

        if os.environ.get("USERINPUT_DEBUG") == "1":
            print(f"DEBUG: Searching for python version: {version}", flush=True)

        # Try to resolve using same logic as PYTHON tool if possible
        system_tag = "macos"
        machine = platform.machine().lower()
        if sys.platform == "darwin":
            if "arm" in machine or "aarch64" in machine:
                system_tag = "macos-arm64"
            else:
                system_tag = "macos"
        elif sys.platform == "linux": 
            system_tag = "linux64" # Simplified
        elif sys.platform == "win32": 
            system_tag = "windows-amd64"

        possible_dirs = [
            version,
            f"{version}-{system_tag}",
            f"{version}-macos-arm64",
            f"{version}-macos",
            f"{version}-linux64",
            f"{version}-linux64-musl",
        ]

        install_root = self.project_root / "tool" / "PYTHON" / "proj" / "install"
        for d in possible_dirs:
            # Unix path
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists():
                return str(python_exec)
            # Windows path
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists():
                return str(python_exec_win)

        # Use shared utility for error reporting
        try:
            from proj.utils import print_python_not_found_error
            print_python_not_found_error(self.tool_name, version, self.script_dir, _)
        except ImportError:
            # Fallback if utility missing
            error_label = _("label_error", "Error")
            print(f"\033[1;31m{error_label}\033[0m: Python tool '{version}' not found.", flush=True)
        
        sys.exit(1)

def get_python_exec(version=None):
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

def get_config():
    config_path = current_dir / "proj" / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def get_user_input_tkinter(title=None, timeout=180, hint_text=None):
    tool = UserInputTool()
    if not tool.check_dependencies():
        raise RuntimeError("Missing dependencies for USERINPUT")

    python_exe = tool.get_python_exe()
    proj_dir = str(tool.script_dir / "proj")
    
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    time_increment = config.get("time_increment", 60)

    if os.environ.get("USERINPUT_DEBUG") == "1":
        print(f"DEBUG: Using python: {python_exe}", flush=True)
        print(f"DEBUG: Proj dir: {proj_dir}", flush=True)
    
    try:
        bell_path = Path(proj_dir) / "tkinter_bell.mp3"
        bell_path_str_literal = repr(str(bell_path))
    except Exception:
        bell_path_str_literal = "''"

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
import traceback
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
    def __init__(self, title, timeout, hint_text, focus_interval, bell_path, time_increment):
        self.root = None
        self.text_widget = None
        self.title = title
        self.remaining_time = timeout
        self.hint_text = hint_text
        self.focus_interval = focus_interval
        self.bell_path = bell_path
        self.time_increment = time_increment
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
            
            tk.Label(main_frame, text=_("instruction", "Please enter your feedback:"), font=("Arial", 10), fg="#555").pack(pady=(0, 10), anchor='w')
            
            text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=7, font=("Arial", 10), bg="#f8f9fa", yscrollcommand=scrollbar.set)
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.text_widget.yview)
            
            if self.hint_text: 
                self.text_widget.insert("1.0", self.hint_text)
            
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
            
            tk.Button(button_frame, text=_("submit", "Submit"), command=self.submit_input, font=("Arial", 10, "bold")).pack(side=tk.RIGHT)
            
            add_time_text = _("add_time", "Add {seconds}s").format(seconds=self.time_increment)
            tk.Button(button_frame, text=add_time_text, command=lambda: self.add_time(self.time_increment), font=("Arial", 10)).pack(side=tk.RIGHT, padx=(0, 10))
            
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 11))
            self.status_label.pack(side=tk.LEFT)
            
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            self.text_widget.focus_set()
            self.start_timer()
            self.start_periodic_focus()
            self.play_bell()
            return True
        except Exception as e:
            traceback.print_exc()
            return False

    def add_time(self, seconds):
        self.remaining_time += seconds
        try:
            added_msg = _("time_added", "Time added! Remaining:")
            self.status_label.config(text=f"{added_msg} {self.remaining_time}s", fg="blue")
            self.root.after(2000, lambda: self.status_label.config(fg="black") if not self.window_closed else None)
        except: pass

    def start_timer(self):
        if self.window_closed: return
        try:
            rem_msg = _('time_remaining', 'Remaining:')
            self.status_label.config(text=f"{rem_msg} {self.remaining_time}s")
        except: pass
        
        if self.remaining_time > 0:
            self.remaining_time -= 1
            if self.root:
                self.root.after(1000, self.start_timer)
        else:
            self.timeout_input()

    def start_periodic_focus(self):
        if self.focus_interval <= 0: return
        def refocus():
            if not self.window_closed and self.root:
                try:
                    self.root.lift()
                    self.root.attributes('-topmost', True)
                    self.play_bell()
                except: pass
                
                if not self.window_closed and self.root:
                    self.root.after(self.focus_interval * 1000, refocus)
        if self.root:
            self.root.after(self.focus_interval * 1000, refocus)

    def play_bell(self):
        if self.root:
            try: self.root.bell()
            except: pass
        if self.bell_path and os.path.exists(self.bell_path):
            def run_play():
                try:
                    if platform.system() == "Darwin":
                        subprocess.run(["afplay", self.bell_path], stderr=subprocess.DEVNULL, timeout=5)
                    elif platform.system() == "Linux":
                        subprocess.run(["aplay", self.bell_path], stderr=subprocess.DEVNULL, timeout=5)
                except: pass
            threading.Thread(target=run_play, daemon=True).start()

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
        try:
            if self.create_window():
                self.root.mainloop()
                print("GDS_USERINPUT_JSON:" + json.dumps(self.result or {"status": "error", "data": "No result"}), flush=True)
        except Exception as e:
            traceback.print_exc()

if __name__ == "__main__":
    try:
        window = TkinterInputWindow(%(title)r, %(timeout)d, %(hint)r, %(focus_interval)d, %(bell_path)r, %(time_increment)d)
        window.run()
    except Exception as e:
        traceback.print_exc()
''' % {
        'project_root': str(tool.project_root),
        'proj_dir': proj_dir,
        'title': title,
        'timeout': timeout,
        'hint': hint_text,
        'focus_interval': focus_interval,
        'bell_path': str(bell_path) if bell_path and bell_path.exists() else '',
        'time_increment': time_increment
    }

    # Use a much longer timeout for communicate to allow for user adding time in GUI
    # The GUI manages its own internal timeout and will exit when it expires.
    # We use a large buffer (3600s) to allow for multiple 'Add 60s' clicks.
    parent_timeout = timeout + 3600 

    try:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as tmp:
            tmp.write(tkinter_script)
            tmp_path = tmp.name

        if os.environ.get("USERINPUT_DEBUG") == "1":
            print(f"DEBUG: Starting subprocess with python: {python_exe} on file {tmp_path}", flush=True)

        proc = subprocess.Popen(
            [python_exe, tmp_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8'
        )
        
        if os.environ.get("USERINPUT_DEBUG") == "1":
            print(f"DEBUG: Subprocess started with PID {proc.pid}. Reading output...", flush=True)
            
            stdout_lines = []
            stderr_lines = []
            
            def read_pipe(pipe, lines, label):
                for line in iter(pipe.readline, ''):
                    print(f"DEBUG_RAW_{label}: {line.strip()}", flush=True)
                    lines.append(line)
                pipe.close()

            t1 = threading.Thread(target=read_pipe, args=(proc.stdout, stdout_lines, "STDOUT"))
            t2 = threading.Thread(target=read_pipe, args=(proc.stderr, stderr_lines, "STDERR"))
            t1.start()
            t2.start()
            
            # Wait for process to finish with timeout
            try:
                proc.wait(timeout=parent_timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                raise UserInputRetryableError(_("msg_timeout", "Timeout"))
            
            t1.join()
            t2.join()
            
            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)
        else:
            # Standard path for normal users
            stdout, stderr = proc.communicate(timeout=parent_timeout) 
        
        # Cleanup temp file
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except:
            pass
        
        if os.environ.get("USERINPUT_DEBUG") == "1":
            print(f"DEBUG: Subprocess finished with code {proc.returncode}", flush=True)
            if stdout: print(f"DEBUG: STDOUT (final): {stdout}", flush=True)
            if stderr: print(f"DEBUG: STDERR (final): {stderr}", flush=True)

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
    parser.add_argument('command', nargs='?', help="Command to run (e.g. setup)")
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    
    # Use ToolBase to handle 'setup' command
    tool = UserInputTool()
    if tool.handle_command_line():
        return 0

    args, unknown = parser.parse_known_args()
    if args.command == "setup": # Fallback if handle_command_line didn't exit
        tool.run_setup()
        return 0

    max_retries = 3
    for attempt in range(max_retries):
        try:
            if os.environ.get("USERINPUT_DEBUG") == "1":
                print(f"DEBUG: Starting attempt {attempt + 1}/{max_retries}...", flush=True)

            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint)
            
            if os.environ.get("USERINPUT_DEBUG") == "1":
                print(f"DEBUG: Success. Result obtained.", flush=True)

            end_hint = "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 指到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
            print(result + end_hint, flush=True)
            
            if platform.system() == "Darwin":
                try: subprocess.run('pbcopy', input=result + end_hint, text=True, encoding='utf-8', check=True)
                except: pass
            return 0
        except (UserInputRetryableError, RuntimeError) as e:
            err_msg = str(e)
            if "Likely due to sandbox restrictions" in err_msg or "No display found" in err_msg:
                # Fatal GUI error, don't retry
                print(f"Fatal error: {err_msg}", file=sys.stderr, flush=True)
                return 1

            if attempt < max_retries - 1:
                msg = _("msg_attempt_failed", "Attempt {index} failed: {error}. Retrying...").format(index=attempt+1, error=e)
                print(msg, file=sys.stderr, flush=True)
                time.sleep(1)
                continue
            final_err = _("msg_failed_capture", "Failed to capture user input: {error}").format(error=e)
            print(f"Error: {final_err}", file=sys.stderr, flush=True)
            return 1

if __name__ == "__main__":
    sys.exit(main())
