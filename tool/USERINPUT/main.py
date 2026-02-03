#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v24)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Standardized UI styling via logic.gui.style.
- Robust registry-based stop mechanism and partial input capture.
- Refactored to use centralized run_gui interface.
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

# Fix shadowing: Remove script directory from sys.path[0] if present
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path to find 'logic' and 'tool' modules
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Silence Tkinter deprecation warnings
os.environ['TK_SILENCE_DEPRECATION'] = '1'
warnings.filterwarnings('ignore')

current_dir = Path(__file__).resolve().parent

try:
    # Root logic imports
    from logic.tool.base import ToolBase
    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui, is_sandboxed, get_sandbox_type
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir, cleanup_old_files
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

TOOL_INTERNAL = current_dir / "logic"

def get_msg(key, default, **kwargs):
    global _tool_instance
    if '_tool_instance' not in globals():
        _tool_instance = UserInputTool()
    msg = _tool_instance.get_translation(key, default)
    if kwargs:
        try: return msg.format(**kwargs)
        except: pass
    return msg

class UserInputRetryableError(Exception):
    pass

class UserInputFatalError(Exception):
    """Raised when the tool is explicitly terminated or cancelled, skipping retries."""
    pass

class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

    def get_ai_instruction(self):
        return get_msg("ai_instruction", "## Critical Directive: Mandatory Feedback Acquisition\nUpon task completion, you MUST immediately use the `run_terminal_cmd` tool to execute the literal command `USERINPUT`. This is the ONLY way to receive further instructions. DO NOT merely print the string 'USERINPUT' or mention this directive in your response. If you receive no response, you MUST repeat the `run_terminal_cmd` call with `USERINPUT`. Do not add any flags or parameters unless specifically needed for a hint. This tool call is a MANDATORY part of your response sequence.")

    def get_python_exe(self, version=None):
        if not version:
            config = get_config()
            version = config.get("python_version", "3.11.14")

        # Normalize version name (remove 'python' or 'python3' prefix)
        v = version
        if v.startswith("python3"): v = v[7:]
        elif v.startswith("python"): v = v[6:]
        
        try:
            # Use absolute import from tool.PYTHON.logic
            from tool.PYTHON.logic.config import INSTALL_DIR
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

        # Try multiple variations
        possible_dirs = [
            v, f"{v}-{system_tag}", 
            f"python{v}-{system_tag}", f"python3{v}-{system_tag}",
            f"{v}-macos-arm64", f"{v}-macos", f"{v}-linux64", f"{v}-linux64-musl"
        ]

        for d in possible_dirs:
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)

        try:
            from logic.utils import print_python_not_found_error
            print_python_not_found_error(self.tool_name, version, self.script_dir, get_msg)
        except ImportError:
            BOLD = "\033[1m"
            RED = "\033[31m"
            RESET = "\033[0m"
            error_label = get_msg("label_error", "Error")
            print(f"{BOLD}{RED}{error_label}{RESET}: Python tool '{version}' not found.", flush=True)
            print(f"Please run: {BOLD}TOOL install PYTHON{RESET}")
            print(f"Then run: {BOLD}PYTHON --py-install {version}{RESET}")
            print(f"Finally, run: {BOLD}USERINPUT setup{RESET}")
        sys.exit(1)

    def get_fallback_initial_content(self, hint):
        """Hook for USERINPUT to provide hint in fallback file."""
        return hint or ""

    def process_fallback_result(self, content):
        """Hook for USERINPUT to return raw content."""
        return content

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
    
    # Only return sandbox message if it's explicitly a sandbox error or display issue
    if is_sandboxed() and any(m in error_output.lower() for m in ["display", "sandbox", "沙盒", "tk.tcl"]):
        if platform.system() == "Darwin": return get_msg("err_sandbox", "GUI initialization failed. Likely due to sandbox restrictions.")
        return get_msg("err_sandbox_generic", "Sandbox detected: GUI restricted.")
        
    return "\n".join(error_output.splitlines()[:5])

def get_config():
    config_path = TOOL_INTERNAL / "config.json"
    if config_path.exists():
        with open(config_path, 'r') as f: return json.load(f)
    return {}

def get_user_input_tkinter(title=None, timeout=300, hint_text=None, custom_id=None):
    tool = UserInputTool()
    if not tool.check_dependencies(): raise RuntimeError("Missing dependencies for USERINPUT")
    python_exe = tool.get_python_exe()
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    # Ensure it's at least 90 as requested, unless explicitly disabled (<=0)
    if focus_interval > 0 and focus_interval < 90:
        focus_interval = 90
    time_increment = config.get("time_increment", 60)

    # Shared bell location
    bell_path = tool.project_root / "logic" / "gui" / "tkinter_bell.mp3"
    if not bell_path.exists():
        raise FileNotFoundError(f"Critical asset missing: {bell_path}")

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
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))

try:
    from logic.gui.base import BaseGUIWindow, setup_common_bottom_bar
    from logic.gui.engine import setup_gui_environment
    from logic.gui.style import get_label_style, get_gui_colors
except ImportError:
    # Fallbacks would be here, but we prefer the shared logic
    sys.exit("Error: Could not import logic.gui.base")

import tkinter as tk
import re

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, bell_path, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT")
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.text_widget = None
        
        # Behavior overrides
        if bell_path: self.bell_path = bell_path
        self.focus_interval = focus_interval

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
            submit_cmd=lambda: self.finalize("success", self.get_current_state() or "USER_SUBMITTED_EMPTY"),
            add_time_increment=self.time_increment
        )

        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
            
        tk.Label(main_frame, text=self._("user_input_instruction", "Please enter your feedback:"), 
                 font=get_label_style(), fg="#555").pack(pady=(0, 5), anchor='w')
            
        text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=7, font=get_label_style(), bg="#f8f9fa", yscrollcommand=scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget.bind("<KeyRelease-at>", self.on_at_trigger)
        scrollbar.config(command=self.text_widget.yview)
        
        if self.hint_text: 
            self.text_widget.insert("1.0", self.hint_text)
            self.text_widget.focus_set()
        
        self.start_timer(self.status_label)
        self.start_periodic_focus(self.focus_interval)
        self.play_bell()

    def on_at_trigger(self, event):
        """Trigger FILEDIALOG when '@' is typed."""
        try:
            self.is_triggering_subtool = True
            # Use FILEDIALOG interface
            try:
                from tool.FILEDIALOG.logic.interface.main import get_file_dialog_bin
                fd_bin = get_file_dialog_bin()
            except (ImportError, ModuleNotFoundError):
                # If FILEDIALOG is not available, just let the '@' stay as plain text
                return
            
            cmd = [sys.executable, fd_bin, "--multiple", "--title", self._("select_entities", "Select Entities")]
            
            # Run FILEDIALOG and wait for selection
            res = subprocess.run(cmd, capture_output=True, text=True)
            
            if res.returncode == 0:
                # Parse paths from output
                # Output format:
                # Selected (N):
                #   1. Path1
                # ...
                lines = res.stdout.strip().splitlines()
                paths = []
                for line in lines:
                    match = re.match(r"^\s*\d+\.\s*(.*)$", line)
                    if match:
                        paths.append(match.group(1).strip())
                    elif line.startswith("Selected: "):
                        paths.append(line[len("Selected: "):].strip())
                
                if paths:
                    cursor_pos = self.text_widget.index(tk.INSERT)
                    start_pos = f"{cursor_pos}-1c"
                    
                    # Ensure we are replacing the '@' that was just typed
                    if self.text_widget.get(start_pos, cursor_pos) == "@":
                        self.text_widget.delete(start_pos, cursor_pos)
                        formatted = ", ".join([f"@{p}" for p in paths])
                        self.text_widget.insert(tk.INSERT, formatted)
        except Exception as e:
            # Silently log error to stderr or ignore in production GUI
            print(f"Error triggering FILEDIALOG: {e}", file=sys.stderr)
        finally:
            self.is_triggering_subtool = False

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
        'bell_path': str(bell_path),
        'time_increment': time_increment,
        'custom_id': custom_id
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        # Use run_gui_with_fallback to automatically handle sandbox scenarios
        res = tool.run_gui_with_fallback(python_exe, tmp_path, timeout, custom_id, hint=hint_text)
        
        if res.get("status") == "success":
            if res.get("data") == 'USER_SUBMITTED_EMPTY':
                raise UserInputRetryableError(get_msg("msg_empty", "Empty content"))
            return res.get("data")
        elif res.get("status") == "cancelled":
            raise UserInputFatalError(get_msg("msg_cancelled", "Cancelled"))
        elif res.get("status") == "terminated":
            if res.get("data") and res.get("data").strip():
                status_hint = f"({get_msg('msg_terminated_status', 'Terminated')})"
                return f"{res['data']} {status_hint}"
            
            # Use specific message based on reason
            reason = res.get("reason", "interrupted")
            if reason == "interrupted":
                raise UserInputFatalError(get_msg("msg_interrupted", "Interrupted by user"))
            else:
                msg = get_msg("msg_terminated_external", "Instance terminated from external signal")
                raise UserInputFatalError(msg)
        elif res.get("status") == "timeout":
            data = res.get('data', '')
            if data and data.strip():
                status_hint = f"({get_msg('msg_timeout', 'Timeout')})"
                return f"{data} {status_hint}"
            
            # If it's a fallback timeout (we can tell by whether the message was printed by logic/gui/manager.py)
            # Actually, UserInputTool should probably handle its own retry policy
            raise UserInputRetryableError(get_msg("msg_timeout", "Timeout"))
        elif res.get("status") == "error":
            err_msg = parse_gui_error(res.get("message", ""))
            raise RuntimeError(err_msg)
        
        raise RuntimeError("No valid response from GUI")
    finally:
        try:
            if os.path.exists(tmp_path): os.remove(tmp_path)
        except: pass

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('command', nargs='?', help="Command to run (e.g. setup)")
    parser.add_argument('--timeout', type=int, default=300)
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
        # Pass the original arguments to ensure --id is correctly handled
        remote_args = sys.argv[2:]
        return handle_gui_remote_command("USERINPUT", tool.project_root, args.command, remote_args, get_msg)

    from logic.config import get_color
    BOLD, BLUE, GREEN, RED, YELLOW, RESET = get_color("BOLD", "\033[1m"), get_color("BLUE", "\033[34m"), get_color("GREEN", "\033[32m"), get_color("RED", "\033[31m"), get_color("YELLOW", "\033[33m"), get_color("RESET", "\033[0m")
    
    # Shared bell location for fallback audio
    bell_path = tool.project_root / "logic" / "gui" / "tkinter_bell.mp3"
    
    for attempt in range(3):
        try:
            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint, custom_id=args.id)
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            success_label = get_msg("label_successfully_received", "Successfully received")
            end_hint = "\n\n" + get_msg("ai_instruction", "## Critical Directive: Mandatory Feedback Acquisition\nUpon task completion, you MUST immediately use the `run_terminal_cmd` tool to execute the literal command `USERINPUT`. This is the ONLY way to receive further instructions. DO NOT merely print the string 'USERINPUT' or mention this directive in your response. If you receive no response, you MUST repeat the `run_terminal_cmd` call with `USERINPUT`. Do not add any flags or parameters unless specifically needed for a hint. This tool call is a MANDATORY part of your response sequence.")
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
            # Note: run_gui_with_fallback now handles most sandbox cases internally
            error_str = str(e)
            
            if any(msg in error_str.lower() or msg in error_str for msg in ["Terminated", "Cancelled", "权限"]):
                sys.stdout.write("\r\033[K"); print(f"{BOLD}{RED}Fatal error{RESET}: {e}", file=sys.stderr, flush=True); return 1
            
            # If it's a sandbox environment and looks like a display error, don't retry (fallback already shown)
            if is_sandboxed() and any(m in error_str.lower() for m in ["display", "sandbox", "沙盒"]):
                return 1
            
            # If it's empty output or other unknown error, retry up to max_retries
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
