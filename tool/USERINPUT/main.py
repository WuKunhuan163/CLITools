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
            from logic.config import get_setting
            version = get_setting("default_python_version", "3.11.14")

        # Normalize version name
        v = version
        if v.startswith("python3"): v = v[7:]
        elif v.startswith("python"): v = v[6:]
        
        try:
            from tool.PYTHON.logic.config import INSTALL_DIR
            install_root = INSTALL_DIR
        except ImportError:
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
    if not tool.check_dependencies(): raise RuntimeError("Missing dependencies for USERINPUT")
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
    from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
    from logic.gui.engine import setup_gui_environment, play_notification_bell
    from logic.gui.tkinter.style import get_label_style
    from logic.utils import find_project_root
except ImportError:
    sys.exit("Error: Could not import GUI blueprint components")

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, time_increment):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT")
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.text_widget = None
        self._last_trigger_time = 0
        self.is_triggering_subtool = False
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
            log_file = self.project_root / "tmp" / "userinput_debug.log"
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
            # Update time IMMEDIATELY to prevent repeat triggers
            self._last_trigger_time = now
            self.root.after(10, self.run_file_dialog_trigger)

    def run_file_dialog_trigger(self):
        if self.is_triggering_subtool:
            self.log_debug("Ignored because subtool already running")
            return
            
        try:
            self.is_triggering_subtool = True
            self.log_debug("Opening FILEDIALOG...")
            
            project_root = %(project_root)r
            fd_bin = Path(project_root) / "bin" / "FILEDIALOG"
            if not fd_bin.exists():
                self.log_debug(f"FILEDIALOG bin not found at {fd_bin}")
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
                    self.log_debug(f"Selection successful: {len(paths)} items inserted.")
            else:
                self.log_debug(f"FILEDIALOG failed: code={res.returncode}, err={res.stderr}")
        except Exception as e:
            self.log_debug(f"Exception in run_file_dialog_trigger: {e}\n{traceback.format_exc()}")
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
                raise UserInputRetryableError(get_msg("msg_empty", "Empty content"))
            return res.get("data")
        elif res.get("status") == "cancelled":
            raise UserInputFatalError(get_msg("msg_cancelled", "Cancelled"))
        elif res.get("status") == "terminated":
            if res.get("data") and res.get("data").strip():
                status_hint = f"({get_msg('msg_terminated_status', 'Terminated')})"
                return f"{res['data']} {status_hint}"
            
            reason = res.get("reason", "interrupted")
            if reason == "interrupted" or reason == "stop":
                raise UserInputFatalError(get_msg("msg_interrupted", "Interrupted by user"))
            elif reason == "signal":
                # External signal (e.g. kill) - allow retry
                raise UserInputRetryableError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
            else:
                raise UserInputFatalError(get_msg("msg_terminated_external", "Instance terminated from external signal"))
        elif res.get("status") == "timeout":
            data = res.get('data', '')
            if data and data.strip():
                # For partial data on timeout, we return it but don't label it 'Successfully received' in main()
                return "__PARTIAL_TIMEOUT__:" + data
            raise UserInputRetryableError(get_msg("msg_timeout", "Timeout"))
        elif res.get("status") == "error":
            err_msg = parse_gui_error(res.get("message", ""))
            raise RuntimeError(err_msg)
            
        raise RuntimeError("No valid response from GUI")
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def main():
    parser = argparse.ArgumentParser(description="USERINPUT Tool")
    parser.add_argument('command', nargs='?', choices=['setup', 'stop', 'submit', 'cancel', 'add_time', 'config', 'rule'], help="Command to run")
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    parser.add_argument('--hint', type=str)
    
    tool = UserInputTool()
    if tool.handle_command_line(parser): return 0
    args, unknown = parser.parse_known_args()
    
    if args.command in ["stop", "submit", "cancel", "add_time"]:
        from logic.gui.manager import handle_gui_remote_command
        return handle_gui_remote_command("USERINPUT", tool.project_root, args.command, sys.argv[2:], tool.get_translation)

    if args.command == "config":
        # Handle config command
        config = get_config()
        updated = False
        
        # We need to parse unknown args for config options
        config_parser = argparse.ArgumentParser(add_help=False)
        config_parser.add_argument("--focus-interval", type=int)
        config_parser.add_argument("--time-increment", type=int)
        config_parser.add_argument("--cpu-limit", type=float)
        config_parser.add_argument("--cpu-timeout", type=int)
        config_parser.add_argument("--system-prompt", type=str)
        config_parser.add_argument("--add-prompt", type=str)
        config_parser.add_argument("--remove-prompt", type=int)
        c_args, _ = config_parser.parse_known_args(unknown)
        
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
            # Migration: if old prompt was a string, convert to list with one item
            config["system_prompt"] = [c_args.system_prompt]
            updated = True
        if c_args.add_prompt is not None:
            prompts = config.get("system_prompt", [])
            if isinstance(prompts, str): prompts = [prompts]
            prompts.append(c_args.add_prompt)
            config["system_prompt"] = prompts
            updated = True
        if c_args.remove_prompt is not None:
            prompts = config.get("system_prompt", [])
            if isinstance(prompts, str): prompts = [prompts]
            if 0 <= c_args.remove_prompt < len(prompts):
                prompts.pop(c_args.remove_prompt)
                config["system_prompt"] = prompts
                updated = True
            
        if updated:
            with open(TOOL_INTERNAL / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            # Print current config
            from logic.config import get_color
            BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
            print(f"{BOLD}{GREEN}Successfully updated{RESET} USERINPUT configuration:")
            for k, v in config.items():
                if k == "system_prompt" and isinstance(v, list):
                    print(f"  {k}:")
                    for i, p in enumerate(v):
                        print(f"    {i}. {p}")
                else:
                    print(f"  {k}: {v}")
            return 0
        else:
            print("Usage: USERINPUT config [--focus-interval <int>] [--time-increment <int>] [--cpu-limit <float>] [--cpu-timeout <int>] [--add-prompt <str>] [--remove-prompt <id>]")
            return 1

    from logic.config import get_color
    BOLD, GREEN, RED, YELLOW, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("YELLOW"), get_color("RESET")

    # AUTO-COMMIT: Save progress before waiting for feedback
    try:
        from tool.GIT.logic.engine import GitEngine
        from logic.turing.logic import TuringStage
        from logic.turing.models.progress import ProgressTuringMachine
        
        git_engine = GitEngine(tool.project_root)
        current_branch = git_engine.get_current_branch()
        
        # Check for changes with timeout
        try:
            status = subprocess.check_output(["/usr/bin/git", "status", "--porcelain"], text=True, cwd=str(tool.project_root), timeout=10).strip()
        except subprocess.TimeoutExpired:
            # If git status hangs, just skip auto-commit
            status = ""
        
        if status:
            # Rolling Tag logic
            tag_file = tool.project_root / "data" / "git" / "tag_counter.txt"
            tag_file.parent.mkdir(parents=True, exist_ok=True)
            curr_tag = 0
            if tag_file.exists():
                try:
                    with open(tag_file, 'r') as f: curr_tag = int(f.read().strip())
                except: pass
            
            next_tag = (curr_tag + 1) % 10000
            with open(tag_file, 'w') as f: f.write(str(next_tag))
            tag_str = f"#{curr_tag:04d}"
            
            ts = time.strftime("%H:%M:%S")
            commit_msg = f"USERINPUT auto-commit {tag_str} at {ts}"
            
            def do_save(stage=None):
                try:
                    subprocess.run(["/usr/bin/git", "add", "."], cwd=str(tool.project_root), capture_output=True, timeout=15)
                    res = subprocess.run(["/usr/bin/git", "commit", "-m", commit_msg], cwd=str(tool.project_root), capture_output=True, text=True, timeout=15)
                    if res.returncode == 0:
                        # Success: Trigger history maintenance check
                        try:
                            # Use base=50 for maintenance
                            git_engine.maintain_history(base=50)
                        except: pass
                        return True
                    else:
                        if stage: 
                            stage.error_brief = f"Commit failed: {res.stderr.strip().splitlines()[-1] if res.stderr.strip() else 'Unknown error'}"
                            stage.error_full = f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                        return False
                except subprocess.TimeoutExpired:
                    if stage: stage.error_brief = "Commit timed out (15s)"
                    return False
                
            def do_backup(stage=None):
                try:
                    res = subprocess.run(["/usr/bin/git", "push", "origin", f"HEAD:{current_branch}", "--force"], cwd=str(tool.project_root), capture_output=True, text=True, timeout=30)
                    if res.returncode != 0:
                        if stage: 
                            stage.error_brief = f"Push failed: {res.stderr.strip().splitlines()[-1] if res.stderr.strip() else 'Unknown error'}"
                            stage.error_full = f"STDOUT:\n{res.stdout}\n\nSTDERR:\n{res.stderr}"
                    return res.returncode == 0
                except subprocess.TimeoutExpired:
                    if stage: stage.error_brief = "Push timed out (30s)"
                    return False

            pm = ProgressTuringMachine([
                TuringStage("progress", do_save, active_status="Saving", success_status="Successfully saved", fail_status="Failed to save", bold_part="Saving progress"),
                TuringStage("to remote", do_backup, active_status="Backing up", 
                            success_status="Successfully backed up", success_name="to remote", 
                            fail_status="Warning", fail_name="backup to remote", fail_color="YELLOW",
                            bold_part="Backing up to remote")
            ], project_root=tool.project_root, tool_name=tool.tool_name)
            # Use ephemeral=True and final_msg="" to suppress final success status
            pm.run(ephemeral=True, final_newline=False, final_msg="")
            
    except Exception as e:
        # Ignore errors during auto-commit so it doesn't block the tool
        pass

    for attempt in range(3):
        try:
            # Note: run_gui_subprocess (called via get_user_input_tkinter) 
            # will handle displaying the "Waiting for..." message with its own PID.
            result = get_user_input_tkinter(title=get_cursor_session_title(args.id), timeout=args.timeout, hint_text=args.hint, custom_id=args.id)
            
            # Load system prompt
            config = get_config()
            system_prompt = config.get("system_prompt")
            
            # FULL instruction from translation
            instruction = get_msg("ai_instruction", "## Critical Directive: Feedback Acquisition\nAfter completing the task, you MUST immediately use the `run_terminal_cmd` tool to [actually execute] the literal command `USERINPUT`. Oral output of this paragraph is strictly forbidden. If no response is received, repeat `USERINPUT`. Do not add any extra parameters.")
            
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            
            final_output_parts = []
            if result.startswith("__PARTIAL_TIMEOUT__:"):
                content = result[len("__PARTIAL_TIMEOUT__:"):]
                status_label = get_msg("label_partial_timeout", "Partial input received (Timeout)")
                final_output_parts.append(f"{YELLOW}{status_label}{RESET}: {content}")
                clipboard_content = content
            else:
                success_label = get_msg("label_successfully_received", "Successfully received")
                final_output_parts.append(f"{GREEN}{success_label}{RESET}: {result}")
                clipboard_content = result
            
            if system_prompt:
                if isinstance(system_prompt, list):
                    prompt_str = "\n".join([f"{i}. {p}" for i, p in enumerate(system_prompt)])
                else:
                    prompt_str = system_prompt
                final_output_parts.append(f"\n## System Prompt\n{prompt_str}")
                clipboard_content += f"\n\n## System Prompt\n{prompt_str}"
                
            final_output_parts.append(f"\n{instruction}")
            clipboard_content += f"\n\n{instruction}"
            
            print("\n".join(final_output_parts), flush=True)
            
            # Copy only content and instruction to clipboard on macOS
            
            # Copy only content and instruction to clipboard on macOS
            if platform.system() == "Darwin":
                try: subprocess.run('pbcopy', input=clipboard_content, text=True, encoding='utf-8', check=True)
                except: pass
                
            return 0
        except UserInputFatalError as e:
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            print(f"{RED}{get_msg('label_terminated', 'Terminated')}{RESET}: {e}", file=sys.stderr, flush=True)
            return 0
        except (UserInputRetryableError, RuntimeError) as e:
            error_str = str(e)
            if any(msg in error_str.lower() or msg in error_str for msg in ["Terminated", "Cancelled"]):
                sys.stdout.write("\r\033[K"); print(f"{RED}Fatal error{RESET}: {e}", file=sys.stderr, flush=True); return 1
            
            if attempt < 2:
                # Use erasable line for retry message
                sys.stdout.write(f"\r\033[KRetry {attempt+1}: {e}")
                sys.stdout.flush()
                time.sleep(1)
            else:
                sys.stdout.write("\r\033[K")
                print(f"{RED}Error{RESET}: {e}. Please execute USERINPUT again and wait for the user.", file=sys.stderr)
                return 1

if __name__ == "__main__":
    sys.exit(main())
