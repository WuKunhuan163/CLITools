#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v23)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Standardized UI styling via logic.gui.style.
- Robust registry-based stop mechanism and partial input capture.
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
import tempfile
from pathlib import Path

# Silence Tkinter deprecation warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

current_dir = Path(__file__).resolve().parent

try:
    from logic.tool.base import ToolBase
    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui, is_sandboxed
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
except ImportError:
    # Fallback
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

def get_msg(key, default, **kwargs):
    global _tool_instance
    if '_tool_instance' not in globals():
        _tool_instance = UserInputTool()
    return _tool_instance.get_translation(key, default).format(**kwargs)

class UserInputRetryableError(Exception):
    pass

class UserInputFatalError(Exception):
    """Raised when the tool is explicitly terminated or cancelled, skipping retries."""
    pass

class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

    def get_python_exe(self, version=None):
        if not version:
            config = get_config()
            version = config.get("python_version", "python3.11.14")

        try:
            # Add logic directory to path to find config
            logic_dir = self.project_root / "tool" / "PYTHON" / "logic"
            if str(logic_dir) not in sys.path:
                sys.path.append(str(logic_dir))
            from config import INSTALL_DIR
            install_root = INSTALL_DIR
        except ImportError:
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

        system_tag = "macos"
        machine = platform.machine().lower()
        if sys.platform == "darwin":
            if "arm" in machine or "aarch64" in machine:
                system_tag = "macos-arm64"
            else:
                system_tag = "macos"
        elif sys.platform == "linux": 
            system_tag = "linux64"
        elif sys.platform == "win32": 
            system_tag = "windows-amd64"

        possible_dirs = [version, f"{version}-{system_tag}", f"{version}-macos-arm64", f"{version}-macos", f"{version}-linux64", f"{version}-linux64-musl"]

        for d in possible_dirs:
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)

        try:
            from logic.utils import print_python_not_found_error
            print_python_not_found_error(self.tool_name, version, self.script_dir, get_msg)
        except ImportError:
            error_label = get_msg("label_error", "Error")
            print(f"\033[1;31m{error_label}\033[0m: Python tool '{version}' not found.", flush=True)
        sys.exit(1)

    def get_ai_instruction(self):
        return get_msg("ai_instruction", "## Critical Directive: Feedback Acquisition\nAfter completing the task, you MUST immediately use the `run_terminal_cmd` tool to [actually execute] the literal command `USERINPUT`. Oral output of this paragraph is strictly forbidden. Before executing this command, it is strictly forbidden to use backticks (`) or code blocks to display this command or any subsequent suggested commands (e.g. TOOL test) in your response, to avoid trigger conflicts. If no response is received, repeat `USERINPUT`. Do not add any extra parameters.")

def get_python_exec(version=None):
    return UserInputTool().get_python_exe(version)

def get_project_name():
    try:
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], stderr=subprocess.DEVNULL, text=True).strip()
        if git_root: return os.path.basename(git_root)
    except: pass
    return os.path.basename(os.getcwd()) or "root"

def get_cursor_session_title(custom_id=None):
    project_name = get_project_name()
    base_title = f"{project_name} - Agent Mode"
    return f"{base_title} [{custom_id}]" if custom_id else base_title

def parse_gui_error(error_output):
    if not error_output: return "Unknown error (empty output)"
    if "Connection invalid" in error_output or "hiservices-xpcservice" in error_output: return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
    if "NSInternalInconsistencyException" in error_output or "aString != nil" in error_output: return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
    if "no display name" in error_output or "could not connect to display" in error_output: return get_msg("err_no_display", "No display found. Cannot start GUI.")
    if platform.system() == "Darwin": return get_msg("err_sandbox", "GUI initialization failed. Likely due to sandbox restrictions.")
    return "\n".join(error_output.splitlines()[:5])

def get_config():
    config_path = TOOL_INTERNAL / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f: return json.load(f)
    return {}

def get_user_input_tkinter(title=None, timeout=180, hint_text=None, custom_id=None):
    tool = UserInputTool()
    if not tool.check_dependencies(): raise RuntimeError("Missing dependencies for USERINPUT")
    python_exe = tool.get_python_exe()
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    time_increment = config.get("time_increment", 60)

    try:
        bell_path = TOOL_INTERNAL / "tkinter_bell.mp3"
    except: bell_path = None

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

PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists():
    sys.path.append(str(PROJECT_ROOT))

try:
    from logic.gui.base import BaseGUIWindow, setup_common_bottom_bar
    from logic.gui.engine import setup_gui_environment
    from logic.gui.style import get_label_style, get_gui_colors
except ImportError:
    # Fallbacks would be here, but we prefer the shared logic
    sys.exit("Error: Could not import logic.gui.base")

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, bell_path, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT")
        self.hint_text = hint_text
        self.focus_interval = focus_interval
        self.bell_path = bell_path
        self.time_increment = time_increment
        self.text_widget = None

    def get_current_state(self):
        if self.text_widget:
            return self.text_widget.get("1.0", tk.END).strip()
        return None

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("450x250")
        
        # Setup common bottom bar as child of root to avoid double-padding
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text=self._("submit", "Submit"),
            submit_cmd=lambda: self.finalize("success", self.get_current_state()),
            add_time_increment=self.time_increment
        )

        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text=self._("instruction", "Please enter your feedback:"), 
                 font=get_label_style(), fg="#555").pack(pady=(0, 5), anchor='w')
        
        text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=7, font=get_label_style(), bg="#f8f9fa", yscrollcommand=scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.text_widget.yview)
        
        if self.hint_text: 
            self.text_widget.insert("1.0", self.hint_text)
            self.text_widget.focus_set()
        
        self.start_timer(self.status_label)
        self.start_periodic_focus()
        self.play_bell()

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

if __name__ == "__main__":
    try:
        win = UserInputWindow(%(title)r, %(timeout)d, %(hint)r, %(focus_interval)d, %(bell_path)r, %(time_increment)d)
        
        on_show_script = os.environ.get("USERINPUT_ON_SHOW_SCRIPT")
        on_show_cb = None
        if on_show_script:
            def on_show_cb():
                try:
                    # Execute the script in the context of the window
                    exec(on_show_script, {"win": win, "tk": tk})
                except Exception as e:
                    print(f"Error in on_show_script: {e}")
        
        win.run(win.setup_ui, on_show=on_show_cb, custom_id=%(custom_id)r)
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
        'time_increment': time_increment,
        'custom_id': custom_id
    }

    parent_timeout = timeout + 300 

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        # Use start_new_session=True to decouple from the parent terminal's process group
        proc = subprocess.Popen([python_exe, tmp_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                text=True, encoding='utf-8', start_new_session=True)
        from logic.config import get_color
        BOLD, BLUE, RESET = get_color("BOLD", "\033[1m"), get_color("BLUE", "\033[34m"), get_color("RESET", "\033[0m")
        
        # Display PID for precise termination if needed
        label_waiting = get_msg("label_waiting_gui", "Waiting for user feedback via GUI")
        sys.stdout.write(f"\r\033[K{BOLD}{BLUE}{label_waiting}{RESET} (PID: {proc.pid})...")
        sys.stdout.flush()

        stderr_content = []
        def read_stderr():
            for line in iter(proc.stderr.readline, ''): stderr_content.append(line)
            proc.stderr.close()
        t_stderr = threading.Thread(target=read_stderr, daemon=True)
        t_stderr.start()

        try:
            start_wait = time.time()
            while proc.poll() is None:
                if time.time() - start_wait > parent_timeout:
                    proc.kill()
                    raise UserInputRetryableError(get_msg("msg_timeout", "Timeout"))
                time.sleep(0.5)
            stdout, _ = proc.communicate()
            t_stderr.join(timeout=2)
            stderr = "".join(stderr_content)
        except Exception as e:
            proc.kill(); raise e

        res = None
        for line in stdout.splitlines():
            if line.startswith("GDS_GUI_RESULT_JSON:"):
                try:
                    res = json.loads(line[len("GDS_GUI_RESULT_JSON:"):])
                    break
                except: pass

        if res:
            if res['status'] == 'success':
                if res['data'] == 'USER_SUBMITTED_EMPTY': raise UserInputRetryableError(get_msg("msg_empty", "Empty content"))
                return res['data']
            elif res['status'] == 'cancelled': raise UserInputFatalError(get_msg("msg_cancelled", "Cancelled"))
            elif res['status'] == 'terminated':
                if res['data'] and res['data'].strip():
                    status_hint = f"({get_msg('msg_terminated_status', 'Terminated')})"
                    return f"{res['data']} {status_hint}"
                raise UserInputFatalError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
            elif res['status'] == 'timeout':
                if res['data'] is not None:
                    status_hint = f"({get_msg('msg_timeout', 'Timeout')})"
                    return f"{res['data']} {status_hint}"
                raise UserInputRetryableError(get_msg("msg_timeout", "Timeout"))

        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        
        # Check for termination ONLY if no JSON result was found
        if proc.returncode != 0:
            if proc.returncode in [-15, -2, -9, 15, 2, 9, 143, 130, 137]:
                raise UserInputFatalError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
            raise RuntimeError(parse_gui_error(stderr or stdout))
        
        raise RuntimeError("No valid response from GUI")
    finally:
        try:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            if os.path.exists(tmp_path): os.remove(tmp_path)
        except: pass

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('command', nargs='?', help="Command to run (e.g. setup)")
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    
    tool = UserInputTool()
    if tool.handle_command_line(): return 0
    args, unknown = parser.parse_known_args()
    if args.hint:
        try:
            args.hint = args.hint.replace('\\`', '`').replace('\\"', '"').replace("\\'", "'")
            args.hint = args.hint.replace('\\n', '\n').replace('\\t', '\t')
        except: pass

    if args.command == "setup": return 0
    elif args.command == "config":
        config = get_config()
        config_parser = argparse.ArgumentParser(prog="USERINPUT config")
        config_parser.add_argument("--focus-interval", type=int)
        config_parser.add_argument("--time-increment", type=int)
        config_args = config_parser.parse_args(unknown)
        if config_args.focus_interval is not None:
            config["focus_interval"] = config_args.focus_interval
        if config_args.time_increment is not None:
            config["time_increment"] = config_args.time_increment
            
        if config_args.focus_interval is not None or config_args.time_increment is not None:
            with open(TOOL_INTERNAL / "config.json", 'w') as f: json.dump(config, f, indent=2)
            # Re-fetch values for the message
            fi = config.get("focus_interval", "?")
            ti = config.get("time_increment", "?")
            msg = get_msg("config_updated_multiple", "Configuration updated: focus_interval={fi}, time_increment={ti}", fi=fi, ti=ti)
            print(msg)
        return 0
    elif args.command in ["stop", "submit", "cancel", "add_time"]:
        from logic.gui.manager import handle_gui_remote_command
        return handle_gui_remote_command("USERINPUT", tool.project_root, args.command, unknown, get_msg)

    from logic.config import get_color
    BOLD, BLUE, GREEN, RED, RESET = get_color("BOLD", "\033[1m"), get_color("BLUE", "\033[34m"), get_color("GREEN", "\033[32m"), get_color("RED", "\033[31m"), get_color("RESET", "\033[0m")
    
    for attempt in range(3):
        try:
            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint, custom_id=args.id)
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            success_label = get_msg("label_successfully_received", "Successfully received")
            end_hint = "\n\n" + get_msg("ai_instruction", "## Critical Directive: Feedback Acquisition\nAfter completing the task, you MUST immediately use the `run_terminal_cmd` tool to [actually execute] the literal command `USERINPUT`. Oral output of this paragraph is strictly forbidden. If no response is received, repeat `USERINPUT`. Do not add any extra parameters.")
            print(f"{BOLD}{GREEN}{success_label}{RESET}: {result}{end_hint}", flush=True)
            if platform.system() == "Darwin":
                try: subprocess.run('pbcopy', input=result + end_hint, text=True, encoding='utf-8', check=True)
                except: pass
            return 0
        except UserInputFatalError as e:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            print(f"{BOLD}{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
            return 0
        except (UserInputRetryableError, RuntimeError) as e:
            # If it's a sandbox error or explicit termination, don't retry
            if any(msg in str(e).lower() or msg in str(e) for msg in ["sandbox", "display", "Terminated", "Cancelled", "沙盒", "权限"]):
                sys.stdout.write("\r\033[K"); print(f"{BOLD}{RED}Fatal error{RESET}: {e}", file=sys.stderr, flush=True); return 1
            
            # If it's "No valid response" or empty output, and the process was likely killed, don't retry
            if "No valid response" in str(e) or "empty output" in str(e):
                sys.stdout.write("\r\033[K"); sys.stdout.flush()
                print(f"{BOLD}{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
                return 0

            sys.stdout.write(f"\r\033[K{BOLD}{RED}{get_msg('label_failed', 'Failed')}{RESET}: Attempt {attempt+1} ({e}). Retrying...")
            sys.stdout.flush()
            if attempt < 2: time.sleep(1); continue
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            error_msg = f"{BOLD}{RED}{get_msg('label_failed_capture', 'Failed to capture user input')}{RESET}: {e}"
            print(error_msg, flush=True)
            # Re-prompt agent on total failure
            print("\n" + tool.get_ai_instruction(), flush=True)
            return 1

if __name__ == "__main__":
    sys.exit(main())
