#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v25)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Standardized UI styling via logic.gui.style.
- Robust registry-based stop mechanism and partial input capture.
- Refactored to use centralized run_gui interface.
- Fixed @ trigger double firing and double quoting.
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
        def handle_command_line(self, parser):
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

    def get_python_exe(self, version=None):
        if not version:
            config = get_config()
            version = config.get("python_version", "3.11.14")

        # Normalize version name
        v = version
        if v.startswith("python3"): v = v[7:]
        elif v.startswith("python"): v = v[6:]
        
        try:
            from tool.PYTHON.logic.config import INSTALL_DIR
            install_root = INSTALL_DIR
        except ImportError:
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

        system_tag = "macos"
        machine = platform.machine().lower()
        if sys.platform == "darwin":
            if "arm" in machine or "aarch64" in machine: system_tag = "macos-arm64"
            else: system_tag = "macos"
        elif sys.platform == "linux": system_tag = "linux64"
        elif sys.platform == "win32": system_tag = "windows-amd64"

        possible_dirs = [v, f"{v}-{system_tag}", f"python{v}-{system_tag}", f"python3{v}-{system_tag}"]
        for d in possible_dirs:
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)
        return sys.executable

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
    if focus_interval > 0 and focus_interval < 90: focus_interval = 90
    time_increment = config.get("time_increment", 60)

    bell_path = tool.project_root / "logic" / "gui" / "tkinter_bell.mp3"
    if not bell_path.exists(): raise FileNotFoundError(f"Asset missing: {bell_path}")

    tkinter_script = r'''
import os
import sys
import json
import time
import subprocess
import platform
import traceback
import shlex
import re
from pathlib import Path

PROJECT_ROOT = Path(%(project_root)r)
if PROJECT_ROOT.exists() and str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from logic.gui.base import BaseGUIWindow, setup_common_bottom_bar
    from logic.gui.engine import setup_gui_environment
    from logic.gui.style import get_label_style
except ImportError:
    sys.exit("Error: Could not import logic.gui.base")

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, bell_path, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT")
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.text_widget = None
        self._last_trigger_time = 0
        self.is_triggering_subtool = False
        self.bell_path = bell_path
        self.focus_interval = focus_interval

    def get_current_state(self):
        if self.text_widget: return self.text_widget.get("1.0", tk.END).strip()
        return None

    def on_submit(self):
        content = self.get_current_state() or "USER_SUBMITTED_EMPTY"
        self.copy_to_clipboard(content)
        self.finalize("success", content)

    def copy_to_clipboard(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            self.log_debug("Copied to clipboard.")
        except Exception as e:
            self.log_debug(f"Clipboard copy failed: {e}")

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("450x250")
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text=self._("submit", "Submit"),
            submit_cmd=self.on_submit,
            add_time_increment=self.time_increment
        )
        main_frame = tk.Frame(self.root, padx=15, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        tk.Label(main_frame, text=self._("user_input_instruction", "Please enter your feedback:"), font=get_label_style(), fg="#555").pack(pady=(0, 5), anchor='w')
        text_frame = tk.Frame(main_frame, relief=tk.FLAT, borderwidth=1)
        text_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_widget = tk.Text(text_frame, wrap=tk.WORD, height=7, font=get_label_style(), bg="#f8f9fa", yscrollcommand=scrollbar.set)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Only bind to Key (press), not KeyRelease, to avoid double trigger
        self.text_widget.bind("<Key>", self.on_any_key)
        scrollbar.config(command=self.text_widget.yview)
        
        if self.hint_text: 
            self.text_widget.insert("1.0", self.hint_text)
            self.text_widget.focus_set()
        self.start_timer(self.status_label)
        self.start_periodic_focus(self.focus_interval)
        self.play_bell()

    def log_debug(self, msg):
        try:
            log_file = PROJECT_ROOT / "tmp" / "userinput_debug.log"
            ts = time.strftime("%%Y-%%m-%%d %%H:%%M:%%S")
            with open(log_file, "a") as f: f.write(f"[{ts}] {msg}\n")
        except: pass

    def on_any_key(self, event):
        # Immediate debounce check
        now = time.time()
        if now - self._last_trigger_time < 0.8: return

        is_shift_2 = (event.keysym == "2" and (event.state & 0x1))
        if event.char == "@" or event.keysym == "at" or is_shift_2:
            self.log_debug(f"on_any_key detected @: char='{event.char}', keysym='{event.keysym}'")
            # Update time IMMEDIATELY to prevent on_any_key_release or repeat triggers
            self._last_trigger_time = now
            self.root.after(10, self.run_file_dialog_trigger)

    def run_file_dialog_trigger(self):
        if self.is_triggering_subtool:
            self.log_debug("Ignored because subtool already running")
            return
            
        try:
            self.is_triggering_subtool = True
            self.log_debug("Opening FILEDIALOG...")
            
            from tool.FILEDIALOG.logic.interface.main import get_file_dialog_bin
            fd_bin = get_file_dialog_bin()
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{PROJECT_ROOT}:{env.get('PYTHONPATH', '')}"
            cmd = [sys.executable, fd_bin, "--multiple", "--title", self._("select_entities", "Select Entities")]
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            if res.returncode == 0:
                output = res.stdout.strip()
                paths = []
                for line in output.splitlines():
                    # Parse FILEDIALOG output format
                    if line.startswith("Selected: "):
                        path = line[len("Selected: "):].strip()
                        paths.append(path)
                    else:
                        match = re.match(r"^\s*\d+\.\s*(.*)$", line)
                        if match:
                            path = match.group(1).strip()
                            paths.append(path)
                
                if paths:
                    # Clean up paths: if they are already quoted (start/end with '), keep them as is
                    # FILEDIALOG quotes paths with spaces.
                    formatted_paths = []
                    for p in paths:
                        if (p.startswith("'") and p.endswith("'")) or (p.startswith('"') and p.endswith('"')):
                            formatted_paths.append(f"@{p}")
                        else:
                            # Path was not quoted by FILEDIALOG (likely no spaces)
                            # But we might want to quote it if it contains spaces just in case
                            q_p = shlex.quote(p) if " " in p else p
                            formatted_paths.append(f"@{q_p}")
                    
                    cursor_pos = self.text_widget.index(tk.INSERT)
                    prev_char = self.text_widget.get(f"{cursor_pos}-1c", cursor_pos)
                    if prev_char == "@": self.text_widget.delete(f"{cursor_pos}-1c", cursor_pos)
                    
                    formatted = ", ".join(formatted_paths)
                    self.text_widget.insert(tk.INSERT, formatted)
                    self.log_debug(f"Selection successful: {len(paths)} items inserted.")
            else:
                self.log_debug(f"FILEDIALOG failed: code={res.returncode}, err={res.stderr}")
        except Exception as e:
            self.log_debug(f"Exception in run_file_dialog_trigger: {e}\n{traceback.format_exc()}")
        finally:
            self.is_triggering_subtool = False
            # Ensure the @ symbol typed isn't processed again soon
            self._last_trigger_time = time.time()

if __name__ == "__main__":
    try:
        win = UserInputWindow(%(title)r, %(timeout)d, %(hint)r, %(focus_interval)d, %(bell_path)r, %(time_increment)d)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except: traceback.print_exc()
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
        res = tool.run_gui_with_fallback(python_exe, tmp_path, timeout, custom_id, hint=hint_text)
        if res.get("status") == "success": return res.get("data")
        elif res.get("status") == "cancelled": raise UserInputFatalError("Cancelled")
        elif res.get("status") == "terminated": return res.get("data") or "Terminated"
        elif res.get("status") == "timeout": return res.get("data") or "Timeout"
        raise RuntimeError(res.get("message", "No valid response from GUI"))
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def get_cursor_session_title(custom_id=None):
    return f"USERINPUT - {custom_id}" if custom_id else "USERINPUT"

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('command', nargs='?', help="Command to run (e.g. setup)")
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    
    tool = UserInputTool()
    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()
    
    if args.command in ["stop", "submit", "cancel", "add_time"]:
        from logic.gui.manager import handle_gui_remote_command
        return handle_gui_remote_command("USERINPUT", tool.project_root, args.command, sys.argv[2:], tool.get_translation)

    try:
        result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint, custom_id=args.id)
        from logic.config import get_color
        BOLD, GREEN, RESET = get_color("BOLD", "\033[1m"), get_color("GREEN", "\033[32m"), get_color("RESET", "\033[0m")
        print(f"{BOLD}{GREEN}Successfully received{RESET}: {result}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
