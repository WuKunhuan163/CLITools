#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v8)
- Captures multi-line user feedback via Tkinter GUI.
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
from pathlib import Path

# Silence Tkinter deprecation warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

# Localization setup
current_dir = Path(__file__).parent.absolute()
project_root = current_dir.parent.parent # Root is two levels up since we are in tool/USERINPUT
python_proj_dir = project_root / "tool" / "PYTHON" / "proj"
if python_proj_dir.exists():
    sys.path.append(str(python_proj_dir.parent))

try:
    from proj.language_utils import get_translation
except ImportError:
    def get_translation(d, k, default): return default

TOOL_PROJ_DIR = current_dir / "proj"

def _(key, default):
    return get_translation(str(TOOL_PROJ_DIR), key, default)

class UserInputRetryableError(Exception):
    """Exception raised for errors that should trigger a retry (e.g., user cancellation)."""
    pass

def get_python_exec(version="python3.10.19"):
    """Find the standalone python executable from the PYTHON tool."""
    python_exec = project_root / "tool" / "PYTHON" / "proj" / "installations" / version / "install" / "bin" / "python3"
    
    if python_exec.exists():
        return str(python_exec)
    
    # Try importing from PYTHON tool utilities if available
    python_utils = project_root / "tool" / "PYTHON" / "proj" / "utils.py"
    if python_utils.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("python_utils", str(python_utils))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.get_python_exec(version)
        except Exception:
            pass
            
    return sys.executable # System fallback

def get_project_name():
    """Retrieve the name of the current project."""
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        if git_root:
            project_name = os.path.basename(git_root)
        else:
            project_name = os.path.basename(os.getcwd())
        return project_name or "root"
    except (subprocess.CalledProcessError, FileNotFoundError):
        project_name = os.path.basename(os.getcwd())
        return project_name or "root"

def get_cursor_session_title(custom_id=None):
    """Generate a title for the Cursor session window."""
    try:
        project_name = get_project_name()
        base_title = f"{project_name} - Agent Mode"
        return f"{base_title} [{custom_id}]" if custom_id else base_title
    except Exception:
        return f"Agent Mode [{custom_id}]" if custom_id else "Agent Mode"

def get_user_input_tkinter(title=None, timeout=180, hint_text=None):
    """
    Captures user input via a Tkinter script run in a separate Python process.
    """
    python_exe = get_python_exec()
    proj_dir = current_dir / "proj"
    
    try:
        bell_path = proj_dir / "tkinter_bell.mp3"
        bell_path_str_literal = repr(str(bell_path))
    except Exception:
        bell_path_str_literal = "''"

    # Python script to be executed in the subprocess
    tkinter_script = f'''
import os
import sys
import warnings
import json
from pathlib import Path
warnings.filterwarnings('ignore')
os.environ['TK_SILENCE_DEPRECATION'] = '1'

import tkinter as tk
import threading
import time
import subprocess
import platform

project_root = Path({repr(str(project_root))})
python_proj_dir = project_root / "tool" / "PYTHON" / "proj"
if python_proj_dir.exists():
    sys.path.append(str(python_proj_dir.parent))

try:
    from proj.language_utils import get_translation
except ImportError:
    def get_translation(d, k, default): return default

TOOL_PROJ_DIR = {repr(str(proj_dir))}

def _(key, default):
    return get_translation(TOOL_PROJ_DIR, key, default)

class TkinterInputWindow:
    def __init__(self, title, timeout, hint_text):
        self.root = None
        self.text_widget = None
        self.status_label = None
        self.title = title
        self.initial_timeout = timeout
        self.hint_text = hint_text
        self.result = None
        self.window_closed = False
        self.remaining_time = self.initial_timeout

    def create_window(self):
        try:
            self.root = tk.Tk()
            self.root.title(self.title)
            self.root.geometry("450x250")
            self.root.attributes('-topmost', True)
            self.root.focus_force()
            main_frame = tk.Frame(self.root, padx=15, pady=15)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            instruction = _("instruction", "Please enter your feedback:")
            instruction_label = tk.Label(main_frame, text=instruction, font=("Arial", 11), fg="#555")
            instruction_label.pack(pady=(0, 10), anchor='w')
            
            text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
            text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.text_widget = tk.Text(
                text_frame, wrap=tk.WORD, height=8, font=("Arial", 12), bg="#f8f9fa",
                fg="#333", insertbackground="#007acc", selectbackground="#007acc",
                relief=tk.FLAT, borderwidth=0, yscrollcommand=scrollbar.set
            )
            self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=self.text_widget.yview)
            if self.hint_text:
                self.text_widget.insert("1.0", self.hint_text)
            button_frame = tk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(0, 10))
            
            default_font = ("Arial", 12)
            submit_font = ("Arial", 13, "bold")
            
            submit_text = _("submit", "Submit")
            submit_btn = tk.Button(button_frame, text=submit_text, command=self.submit_input, font=submit_font)
            submit_btn.pack(side=tk.RIGHT)
            
            add_time_text = _("add_time", "Add 60s")
            add_time_btn = tk.Button(button_frame, text=add_time_text, command=self.add_time, font=default_font)
            add_time_btn.pack(side=tk.RIGHT, padx=(0, 10))
            
            self.status_label = tk.Label(button_frame, text="", font=("Arial", 12), fg="black")
            self.status_label.pack(side=tk.LEFT)
            self.root.bind('<Control-Return>', lambda e: self.submit_input())
            self.root.bind('<Command-Return>', lambda e: self.submit_input())
            self.root.bind('<Escape>', lambda e: self.cancel_input())
            self.root.protocol("WM_DELETE_WINDOW", self.cancel_input)
            self.text_widget.focus_set()
            self.start_timeout_timer()
            self.start_periodic_focus()
            self.play_bell()
            return True
        except Exception:
            import traceback
            print(f"ERROR: Failed to create Tkinter window.\\n{{traceback.format_exc()}}", file=sys.stdout)
            sys.exit(1)

    def add_time(self):
        if self.remaining_time > 0:
            self.remaining_time += 60
            added_text = _("time_added", "Time added! Remaining:")
            try:
                self.status_label.config(text=f"{{added_text}} {{self.remaining_time}}s")
            except tk.TclError: pass

    def start_timeout_timer(self):
        def update_timer():
            time_remaining_text = _("time_remaining", "Remaining:")
            while self.remaining_time > 0 and not self.window_closed:
                try:
                    self.status_label.config(text=f"{{time_remaining_text}} {{self.remaining_time}}s")
                except tk.TclError: break
                time.sleep(1)
                self.remaining_time -= 1
            if not self.window_closed: self.timeout_input()
        threading.Thread(target=update_timer, daemon=True).start()
    
    def start_periodic_focus(self):
        def refocus():
            if not self.window_closed:
                try:
                    if self.root:
                        self.root.lift()
                        self.root.focus_force()
                        self.root.attributes('-topmost', True)
                        self.text_widget.focus_set()
                        self.play_bell()
                        self.root.after(30000, refocus)
                except tk.TclError: pass
        if self.root: self.root.after(30000, refocus)

    def play_bell(self):
        bell_path = {bell_path_str_literal}
        if bell_path and os.path.exists(bell_path):
            def run_play():
                try:
                    if platform.system() == "Darwin":
                        subprocess.run(["afplay", bell_path], stderr=subprocess.DEVNULL)
                    elif platform.system() == "Linux":
                        subprocess.run(["aplay", bell_path], stderr=subprocess.DEVNULL)
                except Exception: pass
            threading.Thread(target=run_play, daemon=True).start()

    def submit_input(self):
        user_text = self.text_widget.get("1.0", tk.END).strip()
        self.result = {{"status": "success", "data": user_text if user_text else "USER_SUBMITTED_EMPTY"}}
        self.close_window()

    def cancel_input(self):
        self.result = {{"status": "cancelled", "data": None}}
        self.close_window()

    def timeout_input(self):
        user_text = self.text_widget.get("1.0", tk.END).strip()
        if user_text:
            self.result = {{"status": "timeout_with_data", "data": user_text}}
        else:
            self.result = {{"status": "timeout", "data": None}}
        self.close_window()

    def close_window(self):
        self.window_closed = True
        try:
            if self.root:
                self.root.quit()
                self.root.destroy()
        except tk.TclError: pass

    def show_and_wait(self):
        if self.create_window():
            self.root.mainloop()
            # Always output JSON for robust communication
            if self.result:
                print(f"GDS_USERINPUT_JSON:{{json.dumps(self.result)}}")
            else:
                print(f"GDS_USERINPUT_JSON:{{json.dumps({{'status': 'error', 'data': 'No result'}})}}")
            sys.exit(0)

if __name__ == "__main__":
    title_str = {repr(title)}
    timeout_int = {timeout}
    hint_text_str = {repr(hint_text)}
    window = TkinterInputWindow(title=title_str, timeout=timeout_int, hint_text=hint_text_str)
    window.show_and_wait()
    '''
    try:
        watchdog_timeout = 3600 # 1 hour
        result = subprocess.run(
            [python_exe, '-c', tkinter_script],
            capture_output=True, text=True, encoding='utf-8', timeout=watchdog_timeout
        )

        if result.returncode != 0:
            error_message = result.stdout.strip() or result.stderr.strip()
            raise RuntimeError(f"USERINPUT subprocess failed: {error_message}")

        output = result.stdout.strip()
        json_prefix = "GDS_USERINPUT_JSON:"
        json_data = None
        
        for line in output.splitlines():
            if line.startswith(json_prefix):
                try:
                    json_data = json.loads(line[len(json_prefix):])
                    break
                except json.JSONDecodeError:
                    continue
        
        if not json_data:
             raise RuntimeError(f"USERINPUT subprocess returned no valid JSON output. Raw output: {output}")

        status = json_data.get("status")
        data = json_data.get("data")

        if status == "success":
            if data == "USER_SUBMITTED_EMPTY":
                raise UserInputRetryableError(_("msg_empty", "User submitted empty content"))
            return data
        elif status == "timeout_with_data":
            # Capturing partial input on timeout
            print(_("msg_timeout", "Input timeout") + f" (Captured partial input)")
            return data
        elif status == "timeout":
            raise UserInputRetryableError(_("msg_timeout", "Input timeout"))
        elif status == "cancelled":
            raise UserInputRetryableError(_("msg_cancelled", "User cancelled input"))
        else:
            raise RuntimeError(f"USERINPUT unknown status: {status}")

    except subprocess.TimeoutExpired:
        raise RuntimeError(f"USERINPUT window timed out after {watchdog_timeout} seconds.")

def main():
    """Main function with retry logic."""
    timeout = 180
    custom_id = None
    hint_text = None
    
    try:
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == '--timeout' and i + 1 < len(args): timeout = int(args[i+1]); i += 2
            elif arg == '--id' and i + 1 < len(args): custom_id = args[i+1]; i += 2
            elif arg == '--hint' and i + 1 < len(args): hint_text = args[i+1]; i += 2
            elif arg in ['--help', '-h']:
                print("Usage: USERINPUT [--timeout SECONDS] [--id CUSTOM_ID] [--hint TEXT]")
                return 0
            else: raise ValueError(f"Unknown parameter: {arg}")
    except (IndexError, ValueError) as e:
        print(f"Parameter error: {e}", file=sys.stderr)
        return 1

    max_retries = 3
    final_result = None
    
    for attempt in range(max_retries):
        try:
            result = get_user_input_tkinter(
                title=get_cursor_session_title(custom_id), timeout=timeout, hint_text=hint_text
            )
            
            end_hint = "\n\n任务完成后，执行终端命令 `USERINPUT` 获取用户反馈。如果程序停止，重复执行 `USERINPUT` 直到获得自然语言反馈。编程遇到不确定的情况或者Keyboard Interrupt时，请执行 `USERINPUT`，不要直接结束。注意：使用 run_terminal_cmd 工具执行的命令就是字面上的 `USERINPUT`，不要添加其他参数或构造交互式命令。"
            final_result = result + end_hint
            break

        except (UserInputRetryableError, RuntimeError) as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1}/{max_retries} failed ({e}), retrying...", file=sys.stderr)
                time.sleep(1)
            continue

    if final_result:
        if platform.system() == "Darwin":
            try:
                subprocess.run('pbcopy', input=final_result, text=True, encoding='utf-8', check=True, stderr=subprocess.DEVNULL)
            except (FileNotFoundError, subprocess.CalledProcessError): pass
        
        print(final_result)
        return 0
    else:
        print("Failed to capture user input. Please run USERINPUT again.", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
