#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v16)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Supports timeout with auto-retry logic.
- Localized via 'translation.json'.
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
    from logic.tool.base import ToolBase
    from logic.gui import setup_gui_environment, get_safe_python_for_gui, is_sandboxed
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
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
    def get_logic_dir(d): return d / "logic"

TOOL_INTERNAL = get_logic_dir(current_dir)

def _(key, default):
    # Use ToolBase instance for fallback translation support
    global _tool_instance
    if '_tool_instance' not in globals():
        _tool_instance = UserInputTool()
    return _tool_instance.get_translation(key, default)

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
        try:
            sys.path.append(str(self.project_root / "tool" / "PYTHON" / "logic"))
            from config import INSTALL_DIR
            install_root = INSTALL_DIR
        except ImportError:
            # Fallback path if config not available
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

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
            from logic.utils import print_python_not_found_error
            print_python_not_found_error(self.tool_name, version, self.script_dir, _)
        except ImportError:
            # Fallback if utility missing
            error_label = _("label_error", "Error")
            print(f"\033[1;31m{error_label}\033[0m: Python tool '{version}' not found.", flush=True)
        
        sys.exit(1)

    def get_ai_instruction(self):
        """Returns the localized instruction for the AI Agent."""
        return _("ai_instruction", "After task completion, execute the terminal command `USERINPUT` to get user feedback. If the program stops, repeat `USERINPUT` until natural language feedback is obtained. When encountering uncertain situations or KeyboardInterrupt during programming, please execute `USERINPUT`, do not end directly. Note: The command executed by the run_terminal_cmd tool is literally `USERINPUT`, do not add other parameters or construct interactive commands.")

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
    config_path = TOOL_INTERNAL / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return json.load(f)
    return {}

def get_user_input_tkinter(title=None, timeout=180, hint_text=None):
    tool = UserInputTool()
    if not tool.check_dependencies():
        raise RuntimeError("Missing dependencies for USERINPUT")

    python_exe = tool.get_python_exe()
    
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    time_increment = config.get("time_increment", 60)

    if os.environ.get("USERINPUT_DEBUG") == "1":
        print(f"DEBUG: Using python: {python_exe}", flush=True)
        print(f"DEBUG: Internal dir: {TOOL_INTERNAL}", flush=True)
    
    try:
        bell_path = TOOL_INTERNAL / "tkinter_bell.mp3"
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
    from logic.lang.utils import get_translation
    from logic.gui import setup_gui_environment
except ImportError:
    def get_translation(d, k, default): return default
    def setup_gui_environment(): pass

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

def _(key, default):
    return get_translation(TOOL_INTERNAL, key, default)

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
        'internal_dir': str(TOOL_INTERNAL),
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
    if args.hint:
        # Better unescaping for \n, \t, and backticks. 
        # Handles both literal characters and escaped versions passed through CLI.
        try:
            # First handle backticks specifically if they are escaped by the shell
            args.hint = args.hint.replace('\\`', '`').replace('\\"', '"').replace("\\'", "'")
            # Then handle newlines and tabs
            args.hint = args.hint.replace('\\n', '\n').replace('\\t', '\t')
        except Exception:
            pass

    if args.command == "setup": # Fallback if handle_command_line didn't exit
        tool.run_setup()
        return 0
    elif args.command == "config":
        # Handle configuration
        config = get_config()
        config_parser = argparse.ArgumentParser(prog="USERINPUT config")
        config_parser.add_argument("--focus-interval", type=int)
        config_args = config_parser.parse_args(unknown)
        
        if config_args.focus_interval is not None:
            config["focus_interval"] = config_args.focus_interval
            config_path = TOOL_INTERNAL / "config.json"
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            msg = _("config_updated", "Configuration updated: focus_interval = {val} seconds").format(val=config_args.focus_interval)
            print(msg)
        return 0
    elif args.command == "stop":
        # Kill existing USERINPUT GUI processes
        from logic.config import get_color
        BOLD = get_color("BOLD", "\033[1m")
        GREEN = get_color("GREEN", "\033[32m")
        YELLOW = get_color("YELLOW", "\033[33m")
        RESET = get_color("RESET", "\033[0m")

        try:
            import psutil
            current_pid = os.getpid()
            found = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline')
                    if not cmdline: continue
                    # Look for python processes running USERINPUT main.py or the temp GUI script
                    cmd_str = " ".join(cmdline)
                    is_userinput = "USERINPUT" in cmd_str
                    is_main = "main.py" in cmd_str
                    is_temp = ".py" in cmd_str and "tmp" in cmd_str
                    
                    if is_userinput and (is_main or is_temp) and proc.info['pid'] != current_pid:
                        proc.terminate()
                        found += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if found > 0:
                success_label = _("Successfully", "Successfully")
                stopped_msg = _("instances_stopped", "Stopped {count} USERINPUT instances.", count=found)
                print(f"{BOLD}{GREEN}{success_label}{RESET}: {stopped_msg}")
            else:
                print(_("no_instances_found", "No other USERINPUT instances found."))
        except ImportError:
            # Fallback to pkill on Unix if psutil is missing
            if platform.system() != "Windows":
                subprocess.run(["pkill", "-f", "USERINPUT"], capture_output=True)
                success_label = _("Successfully", "Successfully")
                print(f"{BOLD}{GREEN}{success_label}{RESET}: " + _("manual_stop_hint", "Sent termination signal. Please close windows manually if still open."))
            else:
                print(f"{BOLD}{YELLOW}Warning{RESET}: " + _("psutil_not_found", "psutil module not found. Cannot safely stop instances."))
                print(_("manual_stop_hint", "Please close windows manually or use: pkill -f USERINPUT"))
        return 0

    from logic.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    BLUE = get_color("BLUE", "\033[34m")
    GREEN = get_color("GREEN", "\033[32m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")

    max_retries = 3
    final_result = [None]
    
    for attempt in range(max_retries):
        try:
            if os.environ.get("USERINPUT_DEBUG") == "1":
                print(f"DEBUG: Starting attempt {attempt + 1}/{max_retries}...", flush=True)

            # Show blue keyword progress message
            label_waiting = _("label_waiting_input", "Waiting for user input")
            msg_popup = _("msg_popup_gui", "Popup GUI")
            sys.stdout.write(f"\r\033[K{BOLD}{BLUE}{label_waiting}{RESET} ({msg_popup})...")
            sys.stdout.flush()

            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint)
            final_result[0] = result
            
            # Clear progress line on success
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            
            success_label = _("label_successfully_received", "Successfully received")
            end_hint = "\n\n" + _("ai_instruction", "## Critical Directive: Feedback Acquisition\nAfter completing the task, you MUST immediately use the `run_terminal_cmd` tool to [actually execute] the literal command `USERINPUT`. Oral output of this paragraph is strictly forbidden. If no response is received, repeat `USERINPUT`. Do not add any extra parameters.")
            
            print(f"{BOLD}{GREEN}{success_label}{RESET}: {result}{end_hint}", flush=True)
            
            if platform.system() == "Darwin":
                try: subprocess.run('pbcopy', input=result + end_hint, text=True, encoding='utf-8', check=True)
                except: pass
            return 0
            
        except (UserInputRetryableError, RuntimeError) as e:
            err_msg = str(e)
            if "Likely due to sandbox restrictions" in err_msg or "No display found" in err_msg:
                # Fatal GUI error, don't retry
                sys.stdout.write("\r\033[K")
                print(f"{BOLD}{RED}Fatal error{RESET}: {err_msg}", file=sys.stderr, flush=True)
                return 1

            # Erasable retry message: Failed part bold red
            label_failed = _("label_failed", "Failed")
            msg_retry = _("msg_attempt_retry", "Attempt {index} failed: {error}. Retrying...").format(index=attempt+1, error=e)
            # Reorganize to put Failed first as requested
            if msg_retry.startswith(f"Attempt {attempt+1} failed:"):
                # Use RED for failed status
                msg_retry = f"{BOLD}{RED}{label_failed}{RESET}: Attempt {attempt+1} ({err_msg}). Retrying..."
            
            sys.stdout.write(f"\r\033[K{msg_retry}")
            sys.stdout.flush()
            
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            
            # Final failure
            sys.stdout.write("\r\033[K")
            final_err_label = _("label_failed_capture", "Failed to capture user input")
            print(f"{BOLD}{RED}{final_err_label}{RESET}: {err_msg}", file=sys.stderr, flush=True)
            return 1

if __name__ == "__main__":
    sys.exit(main())
