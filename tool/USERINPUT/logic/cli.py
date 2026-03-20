"""USERINPUT root entry point — GUI feedback collection.

This is the default behavior when USERINPUT is called with no subcommand
flags (--queue, --system-prompt, --config). It opens a Tkinter GUI window,
collects user feedback, and outputs it with system prompts and directives.

Entry: run_feedback(tool, args) called from main.py
"""
import os
import re
import sys
import time
import tempfile
import subprocess
from pathlib import Path

from tool.USERINPUT.logic import (
    TOOL_INTERNAL, TOOL_DIR, _DEFAULT_AI_INSTRUCTION,
    UserInputRetryableError, UserInputFatalError, _FallbackFileRead,
    get_config, get_msg, get_cursor_session_title, parse_gui_error,
)


def _build_clipboard_suffix():
    """Build the system prompt + critical directive suffix for clipboard."""
    config = get_config()
    system_prompt = config.get("system_prompt")
    instruction_raw = get_msg("ai_instruction", _DEFAULT_AI_INSTRUCTION)
    if "\n\n**" in instruction_raw:
        instruction_part = instruction_raw.split("\n\n**", 1)[0]
    else:
        instruction_part = instruction_raw

    def strip_md(text):
        text = re.sub(r'^##\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        return text

    parts = []
    reflection_prompt = get_msg(
        "label_reflection_prompt",
        "Then run BRAIN reflect to self-check and review system gaps. Then USERINPUT --hint."
    )
    parts.append(f"\n\n{reflection_prompt}")

    full_sp = []
    if system_prompt:
        if isinstance(system_prompt, list):
            full_sp.extend(system_prompt)
        else:
            full_sp.append(system_prompt)
    if full_sp:
        title = get_msg("label_system_prompt", "System Prompt")
        parts.append(f"\n\n{title}")
        for i, p in enumerate(full_sp):
            p = re.sub(r'^(?:\d+[\.\)]|[\-\*])\s*', '', p).strip()
            parts.append(strip_md(f"{i}. {p}"))

    directive_title = get_msg("label_critical_directive", "Critical Directive: USERINPUT Feedback Loop")
    parts.append(f"\n\n{directive_title}")
    clean_instr = re.sub(r'^##\s*[^\n]*\n?', '', instruction_part).strip()
    parts.append(strip_md(clean_instr))
    return "\n".join(parts)


def _save_prompt_if_long(result):
    """Save the user's prompt to data/prompt.txt if it has >20 characters."""
    try:
        text = result
        if isinstance(text, str) and text.startswith("__PARTIAL_TIMEOUT__:"):
            text = text[len("__PARTIAL_TIMEOUT__:"):]
        if text and len(text.strip()) > 20:
            data_dir = TOOL_DIR / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            prompt_file = data_dir / "prompt.txt"
            prompt_file.write_text(text.strip(), encoding="utf-8")
    except Exception:
        pass


def get_user_input_tkinter(title=None, timeout=300, hint_text=None, custom_id=None):
    """Launch Tkinter GUI, collect user input, return text string.

    Raises UserInputRetryableError, UserInputFatalError, or RuntimeError.
    """
    from tool.USERINPUT.logic import _tool_ref
    tool = _tool_ref
    if tool is None:
        from tool.USERINPUT.main import UserInputTool
        tool = UserInputTool()

    if not tool.check_dependencies():
        raise RuntimeError(get_msg("err_missing_dependencies", "Missing dependencies for USERINPUT"))

    python_exe = tool.get_python_exe()
    config = get_config()
    focus_interval = config.get("focus_interval", 90)
    if focus_interval > 0 and focus_interval < 90:
        focus_interval = 90
    time_increment = config.get("time_increment", 60)
    clipboard_suffix = _build_clipboard_suffix()
    success_label = get_msg("label_successfully_received", "Successfully received")
    project_root = str(tool.project_root)

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
    from interface.utils import find_project_root
except ImportError:
    sys.exit("Error: Could not import GUI blueprint components")

import tkinter as tk

TOOL_INTERNAL = %(internal_dir)r

class UserInputWindow(BaseGUIWindow):
    def __init__(self, title, timeout, hint_text, focus_interval, time_increment, clipboard_suffix="", success_label="Successfully received"):
        super().__init__(title, timeout, TOOL_INTERNAL, tool_name="USERINPUT", focus_interval=focus_interval)
        self.hint_text = hint_text
        self.time_increment = time_increment
        self.clipboard_suffix = clipboard_suffix
        self.success_label = success_label
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
        full_clip = f"{self.success_label}: {content}{self.clipboard_suffix}"
        self.copy_to_clipboard(full_clip)
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
        from interface.gui import UndoableText
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
        if now - self._paste_time < 0.5: return

        is_shift_2 = (event.keysym == "2" and (event.state & 0x1))
        if event.char == "@" or event.keysym == "at" or is_shift_2:
            try:
                cursor = self.text_widget.index(tk.INSERT)
                prev_char = self.text_widget.get(f"{cursor}-1c", cursor)
                if prev_char and prev_char.strip():
                    return
            except Exception:
                pass
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
                    if line.startswith("Selected: "):
                        path = line[len("Selected: "):].strip()
                        paths.append(path)
                    else:
                        match = re.match(r"^\s*\d+\.\s*(.*)$", line)
                        if match:
                            path = match.group(1).strip()
                            paths.append(path)
                
                if paths:
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
        except Exception as e:
            pass
        finally:
            self.is_triggering_subtool = False
            self._last_trigger_time = time.time()

if __name__ == "__main__":
    try:
        win = UserInputWindow(%(title)r, %(timeout)d, %(hint)r, %(focus_interval)d, %(time_increment)d, clipboard_suffix=%(clipboard_suffix)r, success_label=%(success_label)r)
        win.run(win.setup_ui, custom_id=%(custom_id)r)
    except: traceback.print_exc()
''' % {
        'project_root': project_root,
        'internal_dir': str(TOOL_INTERNAL),
        'title': title,
        'timeout': timeout,
        'hint': hint_text,
        'focus_interval': focus_interval,
        'time_increment': time_increment,
        'custom_id': custom_id,
        'clipboard_suffix': clipboard_suffix,
        'success_label': success_label
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='USERINPUT_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    _dbg_log_path = Path(project_root) / "tmp" / "userinput_timing.log"
    def _dbg_inner(msg):
        try:
            ts = time.strftime("%H:%M:%S")
            ms = int((time.time() % 1) * 1000)
            with open(_dbg_log_path, "a") as f:
                f.write(f"[{ts}.{ms:03d}]   tkinter: {msg}\n")
        except Exception:
            pass

    _dbg_inner("run_gui_with_fallback BEGIN")
    try:
        res = tool.run_gui_with_fallback(python_exe, tmp_path, timeout, custom_id, hint=hint_text)
        _dbg_inner(f"run_gui_with_fallback END status={res.get('status')}")

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
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def output_result(result, tool, BOLD, GREEN, RED, YELLOW, RESET, from_queue=False, queue_remaining=0):
    """Format and print the result with system prompt and critical directive."""
    _save_prompt_if_long(result)
    config = get_config()
    system_prompt = config.get("system_prompt")
    instruction_raw = get_msg("ai_instruction", _DEFAULT_AI_INSTRUCTION)

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
        final_output_parts.append(f"\n\n{BOLD}{title}{RESET}")
        clipboard_parts.append(f"\n\n## {title}")
        for i, p in enumerate(full_system_prompt_list):
            p = re.sub(r'^(?:\d+[\.\)]|[\-\*])\s*', '', p).strip()
            line = f"{i}. {p}"
            final_output_parts.append(to_ansi_bold(line))
            clipboard_parts.append(strip_markdown(line))

    directive_title = get_msg("label_critical_directive", "Critical Directive: USERINPUT Feedback Loop")
    final_output_parts.append(f"\n\n{BOLD}{directive_title}{RESET}")
    clipboard_parts.append(f"\n\n## {directive_title}")
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


def run_feedback(tool, args):
    """Main feedback flow: open GUI, collect input, output with directives.

    This is the default entry point when USERINPUT is called without
    subcommand flags (--queue, --system-prompt, --config).
    """
    from interface.config import get_color
    BOLD = get_color("BOLD")
    GREEN = get_color("GREEN")
    RED = get_color("RED")
    YELLOW = get_color("YELLOW")
    RESET = get_color("RESET")

    is_enquiry = args.enquiry or get_config().get("enquiry_mode", False)
    if not is_enquiry:
        from tool.USERINPUT.logic.queue import store as qstore
        queued = qstore.claim()
        if queued:
            remaining = qstore.count()
            return output_result(queued, tool, BOLD, GREEN, RED, YELLOW, RESET,
                                 from_queue=True, queue_remaining=remaining)

    hint_text = args.hint
    _fallback_file = None

    _dbg_log = tool.project_root / "tmp" / "userinput_timing.log"
    def _dbg(msg):
        try:
            ts = time.strftime("%H:%M:%S")
            ms = int((time.time() % 1) * 1000)
            with open(_dbg_log, "a") as f:
                f.write(f"[{ts}.{ms:03d}] {msg}\n")
        except Exception:
            pass

    _dbg("=== USERINPUT main() start ===")

    _dbg("fire_hook(on_interaction_start) BEGIN")
    try:
        tool.fire_hook("on_interaction_start", hint=hint_text or "", mode="gui",
                        auto_commit_message=getattr(args, 'auto_commit_message', None) or "")
    except Exception:
        pass
    _dbg("fire_hook(on_interaction_start) END")

    _dbg("gui_launch Turing stage BEGIN")
    try:
        from interface.turing import TuringStage
        _gui_stage = TuringStage(
            "gui_launch", lambda stage=None: True,
            active_status=get_msg("label_launching_gui", "Launching input GUI"),
            active_name="",
            bold_part=get_msg("label_launching_gui", "Launching input GUI"),
        )
        pm_gui = tool.create_progress_machine([_gui_stage])
        pm_gui.run(ephemeral=True, final_newline=False, final_msg="")
    except Exception:
        pass
    _dbg("gui_launch Turing stage END")

    _dbg("get_user_input_tkinter retry loop BEGIN")
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

            result = get_user_input_tkinter(
                title=get_cursor_session_title(args.id),
                timeout=args.timeout,
                hint_text=args.hint,
                custom_id=args.id,
            )
            sys.stdout.write("\r\033[K"); sys.stdout.flush()
            return output_result(result, tool, BOLD, GREEN, RED, YELLOW, RESET)

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
                sys.stdout.write("\r\033[K")
                print(f"{RED}Fatal error{RESET}: {e}", file=sys.stderr, flush=True)
                return 1

            if attempt < 2:
                sys.stdout.write(f"\r\033[KRetry {attempt+1}: {e}")
                sys.stdout.flush()
                time.sleep(1)
            else:
                sys.stdout.write("\r\033[K")
                if not _fallback_file:
                    _fallback_file = str(tool.project_root / "tmp" / "userinput_fallback.txt")
                    Path(_fallback_file).parent.mkdir(parents=True, exist_ok=True)
                    Path(_fallback_file).write_text("", encoding="utf-8")
                fb_msg = (
                    f"\n  {BOLD}Fallback path{RESET}: {_fallback_file}"
                    f"\n  Write your feedback directly to this file. "
                    f"Then run: cat {_fallback_file}"
                )
                print(f"{RED}Error{RESET}: {e}.{fb_msg}", file=sys.stderr)
                return 1
