#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
USERINPUT Tool (v26)
- Captures multi-line user feedback via Tkinter GUI.
- Inherits from ToolBase for dependency management.
- Standardized UI styling via logic.gui.style.
- Robust registry-based stop mechanism and partial input capture.
- Refactored to use centralized run_gui interface.
- RESTORED: Original title, retry logic, timeout handling, and full hint output.
- FIXED: Timeout no longer labeled as 'Successfully received' if empty.
- ENHANCED: Clipboard now includes the full Critical Directive hint.
"""

import os
import sys
import re
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
    from logic.tool.blueprint.base import ToolBase
    from interface.gui import setup_gui_environment, get_safe_python_for_gui, is_sandboxed, get_sandbox_type
    from interface.lang import get_translation
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

class _FallbackFileRead(Exception):
    """Internal: signals that content was read from a fallback file."""
    def __init__(self, content):
        self.content = content

class UserInputTool(ToolBase):
    def __init__(self):
        super().__init__("USERINPUT")

    def get_python_exe(self, version=None):
        if not version:
            from interface.config import get_setting
            version = get_setting("default_python_version", "3.11.14")

        # Normalize version name
        v = version
        if v.startswith("python3"): v = v[7:]
        elif v.startswith("python"): v = v[6:]
        
        try:
            from interface import get_interface
            python_iface = get_interface("PYTHON")
            install_root = python_iface.get_python_install_dir()
        except (ImportError, AttributeError):
            install_root = self.project_root / "tool" / "PYTHON" / "data" / "install"

        from logic.utils import get_system_tag
        system_tag = get_system_tag()

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
    
    # Filter out common macOS/Tkinter system noise
    noise_patterns = [
        "IMKClient subclass",
        "IMKInputSession subclass",
        "chose IMKClient_Legacy",
        "chose IMKInputSession_Legacy",
        "NSInternalInconsistencyException",
        "hiservices-xpcservice"
    ]
    
    lines = error_output.splitlines()
    filtered_lines = [l for l in lines if not any(p in l for p in noise_patterns)]
    
    if not filtered_lines:
        return "GUI process exited without a specific error message (system noise filtered)."

    if "Connection invalid" in error_output: return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
    if "NSInternalInconsistencyException" in error_output or "aString != nil" in error_output: return get_msg("err_sandbox", "Likely due to sandbox restrictions.")
    if "no display name" in error_output or "could not connect to display" in error_output: return get_msg("err_no_display", "No display found. Cannot start GUI.")
    
    # Only return sandbox message if it's explicitly a sandbox error or display issue
    if is_sandboxed() and any(m in error_output.lower() for m in ["display", "sandbox", "沙盒", "tk.tcl"]):
        if platform.system() == "Darwin": return get_msg("err_sandbox", "GUI initialization failed. Likely due to sandbox restrictions.")
        return get_msg("err_sandbox_generic", "Sandbox detected: GUI restricted.")
        
    return "\n".join(filtered_lines[:5])

def get_user_input_tkinter(title=None, timeout=300, hint_text=None, custom_id=None):
    tool = UserInputTool()
    if not tool.check_dependencies(): raise RuntimeError(get_msg("err_missing_dependencies", "Missing dependencies for USERINPUT"))
    python_exe = tool.get_python_exe()
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    if focus_interval > 0 and focus_interval < 90: focus_interval = 90
    time_increment = config.get("time_increment", 60)

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

try:
    from interface.gui import BaseGUIWindow, setup_common_bottom_bar
    from interface.gui import setup_gui_environment, play_notification_bell
    from interface.gui import get_label_style
    from logic.utils import find_project_root
except ImportError:
    sys.exit("Error: Could not import GUI blueprint components")

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT", focus_interval=focus_interval)
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.text_widget = None
        self._last_trigger_time = 0
        self._paste_time = 0
        self._kb_listener = None
        self.is_triggering_subtool = False

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
        except Exception as e:
            pass

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
        from logic.gui.tkinter.widget.text import UndoableText
        self.text_widget = UndoableText.create(
            text_frame, 
            wrap=tk.WORD, 
            height=7, 
            font=get_label_style(), 
            bg="#f8f9fa", 
            yscrollcommand=scrollbar.set
        )
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.text_widget.bind("<Key>", self.on_any_key)
        self.text_widget.bind("<<Paste>>", self._on_paste, add="+")
        scrollbar.config(command=self.text_widget.yview)
        
        if self.hint_text:
            display_hint = self.hint_text.replace("\\n", "\n")
            self.text_widget.insert("1.0", display_hint)
            self.text_widget.focus_set()
        self._start_kb_monitor()
        self.start_timer(self.status_label)

    def _start_kb_monitor(self):
        """Start pynput keyboard monitor to detect Cmd/Ctrl+V globally."""
        try:
            from pynput import keyboard as kb
            _CMD = ('cmd', 'cmd_l', 'cmd_r')
            _CTRL = ('ctrl_l', 'ctrl_r')
            _CMD_VK = (55, 54)
            _state = {"modifier": False}
            window = self

            def on_press(key):
                name = getattr(key, 'name', '')
                char = getattr(key, 'char', '')
                vk = getattr(key, 'vk', None)
                if name in _CMD or name in _CTRL or (vk is not None and vk in _CMD_VK):
                    _state["modifier"] = True
                    return
                if _state["modifier"] and char and char.lower() == 'v':
                    window._paste_time = time.time()

            def on_release(key):
                name = getattr(key, 'name', '')
                vk = getattr(key, 'vk', None)
                if name in _CMD or name in _CTRL or (vk is not None and vk in _CMD_VK):
                    _state["modifier"] = False

            listener = kb.Listener(on_press=on_press, on_release=on_release)
            listener.daemon = True
            listener.start()
            self._kb_listener = listener
        except Exception:
            pass

    def log_debug(self, msg):
        try:
            log_file = self.project_root / "tmp" / "userinput_debug.log"
            ts = time.strftime("%%Y-%%m-%%d %%H:%%M:%%S")
            with open(log_file, "a") as f: f.write(f"[{ts}] {msg}\n")
        except: pass

    def finalize(self, status, data, reason=None):
        if self._kb_listener:
            try: self._kb_listener.stop()
            except: pass
        super().finalize(status, data, reason)

    def _on_paste(self, event):
        self._paste_time = time.time()

    def on_any_key(self, event):
        now = time.time()
        if now - self._last_trigger_time < 0.8: return
        # Skip if a paste operation happened within the last 0.5s
        if now - self._paste_time < 0.5: return

        is_shift_2 = (event.keysym == "2" and (event.state & 0x1))
        if event.char == "@" or event.keysym == "at" or is_shift_2:
            self._last_trigger_time = now
            self.root.after(10, self.run_file_dialog_trigger)

    def run_file_dialog_trigger(self):
        if self.is_triggering_subtool:
            return
            
        try:
            self.is_triggering_subtool = True
            project_root = %(project_root)r
            fd_bin = Path(project_root) / "bin" / "FILEDIALOG" / "FILEDIALOG"
            if not fd_bin.exists():
                fd_bin = Path(project_root) / "bin" / "FILEDIALOG"
            if not fd_bin.exists():
                return
                
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
            cmd = [sys.executable, str(fd_bin), "--multiple", "--title", self._("select_entities", "Select Entities")]
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
                    # Clean up paths: if they are already quoted, keep them as is
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
            else:
                pass
        except Exception as e:
            pass
        finally:
            self.is_triggering_subtool = False
            self._last_trigger_time = time.time()

if __name__ == "__main__":
    try:
        win = UserInputWindow(%(title)r, %(timeout)d, %(hint)r, %(focus_interval)d, %(time_increment)d)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except: traceback.print_exc()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'title': title,
        'timeout': timeout,
        'hint': hint_text,
        'focus_interval': focus_interval,
        'time_increment': time_increment,
        'custom_id': custom_id
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, timeout, custom_id, hint=hint_text)
        
        if res.get("status") == "success":
            if res.get("data") == 'USER_SUBMITTED_EMPTY':
                raise UserInputRetryableError(get_msg("msg_empty_content", "Empty content"))
            return res.get("data")
        elif res.get("status") == "cancelled":
            raise UserInputFatalError(get_msg("msg_cancelled", "Cancelled"))
        elif res.get("status") == "terminated":
            if res.get("data") and res.get("data").strip():
                status_hint = f"({get_msg('msg_terminated_status', 'Terminated')})"
                return f"{res['data']} {status_hint}"
            
            reason = res.get("reason", "interrupted")
            if reason == "interrupted" or reason == "stop":
                raise UserInputFatalError(get_msg("msg_interrupted_by_user", "Interrupted by user"))
            elif reason == "signal":
                # External signal (e.g. kill) - allow retry
                raise UserInputRetryableError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
            else:
                raise UserInputFatalError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
        elif res.get("status") == "timeout":
            data = res.get('data', '')
            fallback_file = res.get('fallback_file', '')
            if data and data.strip():
                return "__PARTIAL_TIMEOUT__:" + data
            if fallback_file:
                raise UserInputRetryableError(
                    get_msg("msg_timeout", "Timeout")
                    + f"\n  Fallback file: {fallback_file}"
                    + "\n  Write your feedback to this file; it will be read on next attempt."
                )
            raise UserInputRetryableError(get_msg("msg_timeout", "Timeout"))
        elif res.get("status") == "error":
            err_msg = parse_gui_error(res.get("message", ""))
            raise RuntimeError(err_msg)
            
        raise RuntimeError(get_msg("err_no_valid_response", "No valid response from GUI"))
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def _handle_queue(tool, args, unknown):
    """Handle all --queue sub-commands."""
    from interface.config import get_color
    BOLD, GREEN, RED, YELLOW, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("RESET")

    _qmod = _load_queue_module()

    has_reorder = any(v is not None for v in [args.move_up, args.move_down, args.move_to_top, args.move_to_bottom])

    queue_label = get_msg("label_queue", "Queue")

    # --queue --list
    if args.list:
        prompts = _qmod.list_all()
        if not prompts:
            print(f"{BOLD}{queue_label}{RESET}: {get_msg('label_queue_empty', 'empty.')}")
            return 0
        n = len(prompts)
        unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
        print(f"{BOLD}{queue_label}{RESET} ({n} {unit}):")
        for i, p in enumerate(prompts):
            display = p if len(p) <= 80 else p[:77] + "..."
            print(f"  {i}: {display}")
        return 0

    # --queue --gui
    if args.gui:
        return _queue_gui(tool)

    # --queue --add "text"
    if args.add:
        _qmod.add(args.add)
        print(f"{BOLD}{GREEN}{get_msg('label_successfully_added', 'Successfully added')}{RESET} {get_msg('label_to_queue', 'to queue')}.")
        return 0

    # --queue --delete <id>
    if args.delete is not None:
        if _qmod.remove(args.delete):
            print(f"{BOLD}{GREEN}{get_msg('label_successfully_deleted', 'Successfully deleted')}{RESET} {get_msg('label_queue_item', 'queue item')} {args.delete}.")
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_delete', 'Failed to delete')}{RESET} {get_msg('label_queue_item', 'queue item')} {args.delete}.", file=sys.stderr)
            return 1
        return 0

    # --queue --move-*
    if has_reorder:
        ops = [
            (args.move_up, _qmod.move_up, get_msg("label_moved_up", "Moved up")),
            (args.move_down, _qmod.move_down, get_msg("label_moved_down", "Moved down")),
            (args.move_to_top, _qmod.move_to_top, get_msg("label_moved_to_top", "Moved to top")),
            (args.move_to_bottom, _qmod.move_to_bottom, get_msg("label_moved_to_bottom", "Moved to bottom")),
        ]
        for val, func, label in ops:
            if val is not None:
                if func(val):
                    print(f"{BOLD}{GREEN}{label}{RESET} {get_msg('label_queue_item', 'item')} {val}.")
                else:
                    print(f"{BOLD}{RED}{get_msg('label_failed_to_move', 'Failed to move')}{RESET} {get_msg('label_queue_item', 'item')} {val}.", file=sys.stderr)
                    return 1
        return 0

    # --queue (no sub-flags) -> open USERINPUT window, save to queue
    return _queue_add_interactive(tool, args)


def _queue_add_interactive(tool, args):
    """Open USERINPUT GUI and save the result to the queue (not displayed)."""
    from interface.config import get_color
    BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")

    try:
        result = get_user_input_tkinter(
            title=get_cursor_session_title(args.id) + " [Queue]",
            timeout=args.timeout,
            hint_text=args.hint,
            custom_id=args.id,
        )
    except UserInputFatalError as e:
        from interface.config import get_color
        RED, RESET = get_color("RED"), get_color("RESET")
        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        print(f"{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
        return 130
    except (UserInputRetryableError, RuntimeError) as e:
        from interface.config import get_color
        RED, RESET = get_color("RED"), get_color("RESET")
        sys.stdout.write("\r\033[K"); sys.stdout.flush()
        print(f"{RED}Error{RESET}: {e}", file=sys.stderr)
        return 1

    if result and result.strip():
        text = result.strip()
        if text.startswith("__PARTIAL_TIMEOUT__:"):
            text = text[len("__PARTIAL_TIMEOUT__:"):]
        if text:
            _qmod = _load_queue_module()
            _qmod.add(text)
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_to_queue', 'to queue')}.")
            return 0

    sys.stdout.write("\r\033[K"); sys.stdout.flush()
    print(f"{BOLD}{get_msg('label_queue', 'Queue')}{RESET}: {get_msg('label_queue_nothing_to_save', 'nothing to save (empty input).')}")
    return 1


def _load_queue_module():
    """Dynamically load the queue module to avoid conflicts with root logic/ package."""
    from importlib.util import spec_from_file_location, module_from_spec
    _spec = spec_from_file_location("userinput_queue", str(TOOL_INTERNAL / "queue.py"))
    _qmod = module_from_spec(_spec)
    _spec.loader.exec_module(_qmod)
    return _qmod


def _queue_gui(tool):
    """Open the editable list GUI for queue management."""
    _qmod = _load_queue_module()
    list_all, replace_all = _qmod.list_all, _qmod.replace_all

    python_exe = tool.get_python_exe()
    items = list_all()

    gui_script = r'''
import os, sys, json, traceback
from pathlib import Path

project_root = %(project_root)r
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interface.gui import setup_gui_environment, EditableListWindow
setup_gui_environment()

items = %(items)r

win = EditableListWindow(
    title="USERINPUT Queue Manager",
    internal_dir=%(internal_dir)r,
    tool_name="USERINPUT",
    items=items,
    list_label="Queued prompts (drag to reorder):",
    save_text="Save",
    cancel_text="Cancel",
    window_size="650x450",
    allow_add=True,
    allow_edit=True,
    allow_delete=True,
)
win.run()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'items': items,
    }

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_queue_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(gui_script)
        tmp_path = tmp.name

    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, 600, None)
        from interface.config import get_color
        BOLD, GREEN, RED, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("RESET")

        if res.get("status") == "success":
            new_items = res.get("data", [])
            if isinstance(new_items, list):
                replace_all(new_items)
                n = len(new_items)
                unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
                print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_queue', 'queue')} ({n} {unit}).")
            return 0
        elif res.get("status") == "cancelled":
            print(f"{BOLD}{get_msg('label_cancelled_queue_editor', 'Cancelled queue editor.')}{RESET}")
            return 0
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_save', 'Failed to save')}{RESET} {get_msg('label_queue', 'queue')}.", file=sys.stderr)
            return 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _handle_config(tool, args, unknown):
    """Handle the 'config' command including system prompt management."""
    config = get_config()
    updated = False

    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument("--focus-interval", type=int)
    config_parser.add_argument("--time-increment", type=int)
    config_parser.add_argument("--cpu-limit", type=float)
    config_parser.add_argument("--cpu-timeout", type=int)
    config_parser.add_argument("--system-prompt", type=str)
    config_parser.add_argument("--add-prompt", type=str)
    config_parser.add_argument("--remove-prompt", type=int)
    config_parser.add_argument("--list", action="store_true")
    config_parser.add_argument("--gui", action="store_true")
    config_parser.add_argument("--move-up", type=int, default=None)
    config_parser.add_argument("--move-down", type=int, default=None)
    config_parser.add_argument("--move-to-top", type=int, default=None)
    config_parser.add_argument("--move-to-bottom", type=int, default=None)
    c_args, _ = config_parser.parse_known_args(unknown)

    # Merge top-level flags that the main parser already consumed
    if args.list: c_args.list = True
    if args.gui: c_args.gui = True
    if args.add and not c_args.add_prompt: c_args.add_prompt = args.add
    if args.delete is not None and c_args.remove_prompt is None: c_args.remove_prompt = args.delete
    if args.move_up is not None: c_args.move_up = args.move_up
    if args.move_down is not None: c_args.move_down = args.move_down
    if args.move_to_top is not None: c_args.move_to_top = args.move_to_top
    if args.move_to_bottom is not None: c_args.move_to_bottom = args.move_to_bottom

    from interface.config import get_color
    BOLD, GREEN, RED, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("RESET")

    prompts = config.get("system_prompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]

    sp_label = get_msg("label_system_prompts", "System prompts")

    # --list: show system prompts
    if c_args.list:
        if not prompts:
            print(f"{BOLD}{sp_label}{RESET}: {get_msg('label_system_prompts_empty', 'empty.')}")
        else:
            n = len(prompts)
            unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
            print(f"{BOLD}{sp_label}{RESET} ({n} {unit}):")
            for i, p in enumerate(prompts):
                display = p if len(p) <= 80 else p[:77] + "..."
                print(f"  {i}: {display}")
        return 0

    # --gui: open GUI for system prompt management
    if c_args.gui:
        return _config_prompt_gui(tool, config)

    # --move-* for system prompts
    has_reorder = any(v is not None for v in [c_args.move_up, c_args.move_down, c_args.move_to_top, c_args.move_to_bottom])
    if has_reorder:
        label_map = {
            "up": get_msg("label_moved_up", "Moved up"),
            "down": get_msg("label_moved_down", "Moved down"),
            "top": get_msg("label_moved_to_top", "Moved to top"),
            "bottom": get_msg("label_moved_to_bottom", "Moved to bottom"),
        }
        ops = [
            (c_args.move_up, "up"),
            (c_args.move_down, "down"),
            (c_args.move_to_top, "top"),
            (c_args.move_to_bottom, "bottom"),
        ]
        sp_item = get_msg("label_system_prompt_item", "system prompt")
        for val, direction in ops:
            if val is not None:
                ok = _reorder_prompt(prompts, val, direction)
                if ok:
                    config["system_prompt"] = prompts
                    with open(TOOL_INTERNAL / "config.json", 'w') as f:
                        json.dump(config, f, indent=2, ensure_ascii=False)
                    print(f"{BOLD}{GREEN}{label_map[direction]}{RESET} {sp_item} {val}.")
                else:
                    print(f"{BOLD}{RED}{get_msg('label_failed_to_move', 'Failed to move')}{RESET} {sp_item} {val}.", file=sys.stderr)
                    return 1
        return 0

    if c_args.focus_interval is not None:
        config["focus_interval"] = c_args.focus_interval
        updated = True
    if c_args.time_increment is not None:
        config["time_increment"] = c_args.time_increment
        updated = True
    if c_args.cpu_limit is not None:
        config["cpu_limit"] = c_args.cpu_limit
        updated = True
    if c_args.cpu_timeout is not None:
        config["cpu_timeout"] = c_args.cpu_timeout
        updated = True
    if c_args.system_prompt is not None:
        config["system_prompt"] = [c_args.system_prompt]
        updated = True
    if c_args.add_prompt is not None:
        prompts.append(c_args.add_prompt)
        config["system_prompt"] = prompts
        updated = True
    if c_args.remove_prompt is not None:
        if 0 <= c_args.remove_prompt < len(prompts):
            prompts.pop(c_args.remove_prompt)
            config["system_prompt"] = prompts
            updated = True

    if updated:
        with open(TOOL_INTERNAL / "config.json", 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        print(f"{BOLD}{GREEN}{get_msg('label_successfully_updated', 'Successfully updated')}{RESET} USERINPUT configuration:")
        for k, v in config.items():
            if k == "system_prompt" and isinstance(v, list):
                print(f"  {k}:")
                for i, p in enumerate(v):
                    print(f"    {i}. {p}")
            else:
                print(f"  {k}: {v}")
        return 0
    else:
        print("Usage: USERINPUT config [--focus-interval <int>] [--time-increment <int>]")
        print("  System prompts: --add <str> | --delete <id> | --list | --gui")
        print("  (aliases:        --add-prompt <str> | --remove-prompt <id>)")
        print("  Reorder:        --move-up <id> | --move-down <id> | --move-to-top <id> | --move-to-bottom <id>")
        return 1


def _reorder_prompt(prompts, index, direction):
    """Reorder an item in a list in-place. Returns True on success."""
    n = len(prompts)
    if index < 0 or index >= n:
        return False
    if direction == "up":
        if index <= 0: return False
        prompts[index - 1], prompts[index] = prompts[index], prompts[index - 1]
    elif direction == "down":
        if index >= n - 1: return False
        prompts[index], prompts[index + 1] = prompts[index + 1], prompts[index]
    elif direction == "top":
        if index <= 0: return False
        item = prompts.pop(index)
        prompts.insert(0, item)
    elif direction == "bottom":
        if index >= n - 1: return False
        item = prompts.pop(index)
        prompts.append(item)
    else:
        return False
    return True


def _config_prompt_gui(tool, config):
    """Open the editable list GUI for system prompt management."""
    prompts = config.get("system_prompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]

    python_exe = tool.get_python_exe()

    gui_script = r'''
import os, sys, json, traceback
from pathlib import Path

project_root = %(project_root)r
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from interface.gui import setup_gui_environment, EditableListWindow
setup_gui_environment()

items = %(items)r

win = EditableListWindow(
    title="USERINPUT System Prompts",
    internal_dir=%(internal_dir)r,
    tool_name="USERINPUT",
    items=items,
    list_label="System prompts:",
    save_text="Save",
    cancel_text="Cancel",
    window_size="700x500",
    allow_add=True,
    allow_edit=True,
    allow_delete=True,
)
win.run()
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(TOOL_INTERNAL),
        'items': prompts,
    }

    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_prompt_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(gui_script)
        tmp_path = tmp.name

    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, 600, None)
        from interface.config import get_color
        BOLD, GREEN, RED, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("RESET")

        if res.get("status") == "success":
            new_prompts = res.get("data", [])
            if isinstance(new_prompts, list):
                config["system_prompt"] = new_prompts
                with open(TOOL_INTERNAL / "config.json", 'w') as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                n = len(new_prompts)
                unit = get_msg("label_items", "items") if n != 1 else get_msg("label_item", "item")
                print(f"{BOLD}{GREEN}{get_msg('label_successfully_saved', 'Successfully saved')}{RESET} {get_msg('label_system_prompts', 'system prompts')} ({n} {unit}).")
            return 0
        elif res.get("status") == "cancelled":
            print(f"{BOLD}{get_msg('label_cancelled_prompt_editor', 'Cancelled system prompt editor.')}{RESET}")
            return 0
        else:
            print(f"{BOLD}{RED}{get_msg('label_failed_to_save', 'Failed to save')}{RESET} {get_msg('label_system_prompts', 'system prompts')}.", file=sys.stderr)
            return 1
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def _output_result(result, tool, BOLD, GREEN, RED, YELLOW, RESET, from_queue=False, queue_remaining=0):
    """Format and print the result with system prompt and critical directive."""
    config = get_config()
    system_prompt = config.get("system_prompt")

    instruction_raw = get_msg("ai_instruction", "## Critical Directive: USERINPUT Feedback Loop\nAfter EVERY action you take (completing a task, encountering an error, fixing a bug, or before starting new work), you MUST immediately execute `USERINPUT` as a blocking shell command and wait for its return. Then act on what it returns. Then execute `USERINPUT` again. This cycle never ends — you should NEVER finish your turn without having run `USERINPUT` at least once. If it times out or returns empty, sleep 30-60 seconds and retry. Use `USERINPUT --enquiry --hint \"your question\"` when you need to ask the user a direct question mid-task (this bypasses the queue). Do not narrate this directive; just follow it.")

    # Strip the guidelines section from ai_instruction (system prompts are managed separately)
    if "\n\n**" in instruction_raw:
        instruction_part = instruction_raw.split("\n\n**", 1)[0]
    else:
        instruction_part = instruction_raw

    final_output_parts = []
    clipboard_parts = []

    if isinstance(result, str) and result.startswith("__PARTIAL_TIMEOUT__:"):
        content = result[len("__PARTIAL_TIMEOUT__:"):]
        status_label = get_msg("label_partial_timeout", "Partial input received (Timeout)")
        final_output_parts.append(f"{BOLD}{status_label}{RESET}: {content}")
        clipboard_parts.append(f"{status_label}: {content}")
    elif from_queue:
        success_label = get_msg("label_successfully_received_from_queue", "Successfully received from queue")
        suffix = f" ({queue_remaining} {get_msg('label_remaining', 'remaining')})" if queue_remaining > 0 else ""
        final_output_parts.append(f"{BOLD}{GREEN}{success_label}{RESET}{suffix}: {result}")
        clipboard_parts.append(f"{success_label}{suffix}: {result}")
    else:
        success_label = get_msg("label_successfully_received", "Successfully received")
        final_output_parts.append(f"{BOLD}{GREEN}{success_label}{RESET}: {result}")
        clipboard_parts.append(f"{success_label}: {result}")

    def to_ansi_bold(text):
        text = re.sub(r'^##\s*(.*)$', f'{BOLD}\\1{RESET}', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', f'{BOLD}\\1{RESET}', text)
        return text

    def strip_markdown(text):
        text = re.sub(r'^##\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        return text

    full_system_prompt_list = []
    if system_prompt:
        if isinstance(system_prompt, list):
            full_system_prompt_list.extend(system_prompt)
        else:
            full_system_prompt_list.append(system_prompt)

    if full_system_prompt_list:
        title = get_msg("label_system_prompt", "System Prompt")
        final_output_parts.append(f"\n{BOLD}{title}{RESET}")
        clipboard_parts.append(f"\n## {title}")

        for i, p in enumerate(full_system_prompt_list):
            p = re.sub(r'^(?:\d+[\.\)]|[\-\*])\s*', '', p).strip()
            line = f"{i}. {p}"
            final_output_parts.append(to_ansi_bold(line))
            clipboard_parts.append(strip_markdown(line))

    directive_title = get_msg("label_critical_directive", "Critical Directive: USERINPUT Feedback Loop")
    final_output_parts.append(f"\n{BOLD}{directive_title}{RESET}")
    clipboard_parts.append(f"\n## {directive_title}")

    clean_instruction = re.sub(r'^##\s*[^\n]*\n?', '', instruction_part).strip()
    final_output_parts.append(to_ansi_bold(clean_instruction))
    clipboard_parts.append(strip_markdown(clean_instruction))

    print("\n".join(final_output_parts), flush=True)

    try:
        clipboard_text = "\n".join(clipboard_parts)
        proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
        proc.communicate(clipboard_text.encode("utf-8"))
    except Exception:
        pass

    return 0


def main():
    tool = UserInputTool()

    # Early intercept remote GUI control commands (--gui-submit, --gui-cancel, --gui-stop, --gui-add-time)
    _gui_cmd_map = {"--gui-submit": "submit", "--gui-cancel": "cancel", "--gui-stop": "stop", "--gui-add-time": "add_time"}
    _gui_match = next((f for f in _gui_cmd_map if f in sys.argv), None)
    if _gui_match:
        from interface.gui import handle_gui_remote_command
        remaining = [a for a in sys.argv[1:] if a not in _gui_cmd_map and a != "--no-warning"]
        return handle_gui_remote_command("USERINPUT", tool.project_root, _gui_cmd_map[_gui_match], remaining, tool.get_translation)

    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('command', nargs='?', choices=['setup', 'config', 'rule'], help="Command to run")
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    parser.add_argument('--queue', action='store_true', help="Queue mode: add to queue or manage queue")
    parser.add_argument('--enquiry', action='store_true', help="Bypass queue, request real-time user feedback")
    parser.add_argument('--list', action='store_true', help="List items (queue or system prompts)")
    parser.add_argument('--gui', action='store_true', help="Open GUI manager (queue or system prompts)")
    parser.add_argument('--add', type=str, metavar='TEXT', help="Add item (to queue or system prompts)")
    parser.add_argument('--delete', type=int, metavar='ID', default=None, help="Delete item by index")
    parser.add_argument('--move-up', type=int, metavar='ID', default=None)
    parser.add_argument('--move-down', type=int, metavar='ID', default=None)
    parser.add_argument('--move-to-top', type=int, metavar='ID', default=None)
    parser.add_argument('--move-to-bottom', type=int, metavar='ID', default=None)
    
    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()

    # ── Queue management ───────────────────────────────────
    if args.queue:
        return _handle_queue(tool, args, unknown)

    # ── Config command (includes system prompt management) ─
    if args.command == "config":
        return _handle_config(tool, args, unknown)

    # --list / --gui / --move-* / --add / --delete without --queue or config are invalid
    mgmt_flags = args.list or args.gui or args.add or args.delete is not None
    mgmt_flags = mgmt_flags or any(v is not None for v in [args.move_up, args.move_down, args.move_to_top, args.move_to_bottom])
    if mgmt_flags:
        print("Usage: --list, --gui, --add, --delete, --move-* require --queue or config command.", file=sys.stderr)
        return 1

    from interface.config import get_color
    BOLD, GREEN, RED, YELLOW, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("RESET")

    # ── Queue claiming (unless --enquiry bypasses it) ─────
    if not args.enquiry:
        _qmod = _load_queue_module()
        queued = _qmod.claim()
        if queued:
            remaining = _qmod.count()
            return _output_result(queued, tool, BOLD, GREEN, RED, YELLOW, RESET, from_queue=True, queue_remaining=remaining)

    hint_text = args.hint

    # Fire on_interaction_start hooks (includes auto-save-remote if enabled)
    try:
        tool.fire_hook("on_interaction_start", hint=hint_text or "", mode="gui")
    except Exception:
        pass

    _fallback_file = None

    for attempt in range(3):
        try:
            if attempt > 0 and _fallback_file and Path(_fallback_file).exists():
                fb = Path(_fallback_file)
                if fb.stat().st_size > 0:
                    content = fb.read_text(encoding="utf-8").strip()
                    if content:
                        result = content
                        fb.unlink(missing_ok=True)
                        _fallback_file = None
                        sys.stdout.write("\r\033[K"); sys.stdout.flush()
                        raise _FallbackFileRead(result)

            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint, custom_id=args.id)
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            return _output_result(result, tool, BOLD, GREEN, RED, YELLOW, RESET)

        except _FallbackFileRead as fb:
            result = fb.content
            from_file_label = get_msg("label_from_fallback_file", "Received from fallback file")
            print(f"{BOLD}{GREEN}{from_file_label}{RESET}: {result}")
            return 0
        except UserInputFatalError as e:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            print(f"{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
            return 130
        except (UserInputRetryableError, RuntimeError) as e:
            error_str = str(e)
            if "Fallback file:" in error_str:
                import re as _re
                m = _re.search(r'Fallback file:\s*(.+)', error_str)
                if m:
                    _fallback_file = m.group(1).strip()

            if any(msg in error_str.lower() or msg in error_str for msg in ["Terminated", "Cancelled"]):
                sys.stdout.write("\r\033[K"); print(f"{RED}Fatal error{RESET}: {e}", file=sys.stderr, flush=True); return 1
            
            if attempt < 2:
                sys.stdout.write(f"\r\033[KRetry {attempt+1}: {e}")
                sys.stdout.flush()
                time.sleep(1)
            else:
                sys.stdout.write("\r\033[K")
                fb_msg = ""
                if _fallback_file:
                    fb_msg = f"\n  Fallback: write feedback to {_fallback_file}"
                print(f"{RED}Error{RESET}: {e}.{fb_msg}", file=sys.stderr)
                return 1

if __name__ == "__main__":
    sys.exit(main())
