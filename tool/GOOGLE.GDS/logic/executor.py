#!/usr/bin/env python3 -u
import os
import json
import time
import hashlib
import subprocess
from pathlib import Path

def generate_remote_command_script(project_root: Path, command: str, remote_cwd: str = "/content/drive/MyDrive/REMOTE_ROOT", as_python: bool = False, shell_type: str = "bash", finished_msg: str = "", executing_msg: str = "", finished_label: str = "", cdp_mode: bool = False):
    """
    Generates a script to be executed in Colab that runs a shell command
    and writes the result back to Google Drive.

    When as_python=True or cdp_mode=True, generates clean Python cell code
    with visible output. Otherwise generates a bash script for terminal pasting.
    """
    config_path = project_root / "data" / "config.json"
    mount_hash = ""
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                mount_hash = json.load(f).get("mount_hash", "")
        except: pass

    ts = str(int(time.time()))
    cmd_hash = hashlib.md5(f"{ts}_{command}".encode()).hexdigest()[:8]
    
    result_filename = f"result_{ts}_{cmd_hash}.json"

    if cdp_mode or as_python:
        script_template = _generate_cdp_cell_code(
            command, remote_cwd, False, mount_hash, ts, cmd_hash,
            result_filename, shell_type, finished_msg, executing_msg, finished_label
        )
        return script_template, {
            "ts": ts,
            "hash": cmd_hash,
            "result_filename": result_filename,
            "done_marker": f"GDS_DONE_{cmd_hash}"
        }

    # Bash terminal version: write a self-contained script to /tmp then execute it.
    import shlex
    script_id = f"{ts}_{cmd_hash}"

    inner_script = f'''#!/bin/bash
if [ ! -d "/content/drive/MyDrive" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Google Drive is not mounted. Run '\\033[1mGDS --remount\\033[0m' locally first."
    exit 1
fi

if [ -n "{mount_hash}" ] && [ ! -f "/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_{mount_hash}" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Mount fingerprint validation failed. Run '\\033[1mGDS --remount\\033[0m' locally to resync."
    exit 1
fi

mkdir -p "{remote_cwd}"
cd "{remote_cwd}"

OUTPUT_FILE="/tmp/gcs_stdout_{script_id}"
ERROR_FILE="/tmp/gcs_stderr_{script_id}"
RESULT_BASE="/content/drive/MyDrive/REMOTE_ENV/tmp"
mkdir -p "$RESULT_BASE"
RESULT_FILE="$RESULT_BASE/{result_filename}"

echo "{executing_msg or 'Executing'} command..."

SHELL_BIN="{shell_type}"
if [ "{shell_type}" != "bash" ] && [ "{shell_type}" != "sh" ]; then
    CUSTOM_SHELL="/content/drive/MyDrive/REMOTE_ENV/shell/{shell_type}/bin/{shell_type}"
    if [ -x "$CUSTOM_SHELL" ]; then
        SHELL_BIN="$CUSTOM_SHELL"
    elif command -v "{shell_type}" > /dev/null 2>&1; then
        SHELL_BIN="{shell_type}"
    else
        echo "Warning: {shell_type} not found, falling back to bash" >&2
        SHELL_BIN="bash"
    fi
fi

set +e
trap '' PIPE
$SHELL_BIN << 'USER_COMMAND_EOF' > "$OUTPUT_FILE" 2> "$ERROR_FILE"
{command}
USER_COMMAND_EOF
EXIT_CODE=$?
set -e

if [ -s "$ERROR_FILE" ]; then
    cat "$ERROR_FILE" >&2
fi

echo "Command finished with exit code $EXIT_CODE. Saving result..."

export GDS_EXIT_CODE=$EXIT_CODE
export GDS_TIMESTAMP="{ts}"
export GDS_COMMAND={shlex.quote(command)}
export GDS_RESULT_FILE="$RESULT_FILE"
export GDS_STDOUT_FILE="$OUTPUT_FILE"
export GDS_STDERR_FILE="$ERROR_FILE"

python3 -c '
import json, os
from datetime import datetime
sf = os.environ["GDS_STDOUT_FILE"]
ef = os.environ["GDS_STDERR_FILE"]
so = open(sf, "r", errors="ignore").read() if os.path.exists(sf) else ""
se = open(ef, "r", errors="ignore").read() if os.path.exists(ef) else ""
r = {{"command": os.environ["GDS_COMMAND"], "stdout": so, "stderr": se, "returncode": int(os.environ["GDS_EXIT_CODE"]), "duration": 0, "timestamp": os.environ["GDS_TIMESTAMP"], "completed": datetime.now().isoformat()}}
with open(os.environ["GDS_RESULT_FILE"], "w") as f: json.dump(r, f, indent=2, ensure_ascii=False)
'

rm -f "$OUTPUT_FILE" "$ERROR_FILE"
clear
echo -e "\\033[1m{finished_label or 'GDS Remote Command'} [{cmd_hash.upper()}]\\033[0m: {finished_msg or 'Execution completed and result saved. You may now press the Finished button.'}"
echo "GDS_DONE_{cmd_hash}"
'''

    script_template = f'''cat > /tmp/gcs_run_{script_id}.sh << 'GDS_SCRIPT_EOF'
{inner_script}GDS_SCRIPT_EOF
bash /tmp/gcs_run_{script_id}.sh ; rm -f /tmp/gcs_run_{script_id}.sh'''

    return script_template, {
        "ts": ts,
        "hash": cmd_hash,
        "result_filename": result_filename,
        "done_marker": f"GDS_DONE_{cmd_hash}"
    }

def _generate_cdp_cell_code(command, remote_cwd, as_python, mount_hash, ts,
                            cmd_hash, result_filename, shell_type, finished_msg,
                            executing_msg, finished_label):
    """Generate clean Python cell code for CDP injection.

    The output is designed to be readable in a Colab Python cell with
    command output visible in the cell output area.
    """
    result_path = f"/content/drive/MyDrive/REMOTE_ROOT/tmp/{result_filename}"
    done_marker = f"GDS_DONE_{cmd_hash}"
    exec_msg = executing_msg or "Executing"
    fin_label = finished_label or "Finished"
    fin_msg = finished_msg or "Execution completed."

    if as_python:
        runner = f"_r = subprocess.run(['python3', '-c', _CMD], capture_output=True, text=True, cwd=_CWD)"
    elif shell_type not in ("bash", "sh"):
        runner = (
            f"_custom = '/content/drive/MyDrive/REMOTE_ENV/shell/{shell_type}/bin/{shell_type}'\n"
            f"_shell = _custom if os.path.isfile(_custom) and os.access(_custom, os.X_OK) else '{shell_type}'\n"
            "_r = subprocess.run([_shell, '-c', _CMD], capture_output=True, text=True, cwd=_CWD)"
        )
    else:
        runner = "_r = subprocess.run(['bash', '-c', _CMD], capture_output=True, text=True, cwd=_CWD)"

    return f'''import subprocess, json, os, time
from datetime import datetime

_CWD = {repr(remote_cwd)}
_CMD = {repr(command)}
_HASH = {repr(mount_hash)}
_TS = {repr(ts)}
_RESULT = {repr(result_path)}

if not os.path.isdir('/content/drive/MyDrive'):
    print('\\033[1mError\\033[0m: Google Drive not mounted. Run GDS --remount.')
    raise SystemExit(1)
if _HASH and not os.path.exists(f'/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_{{_HASH}}'):
    print('\\033[1mError\\033[0m: Mount fingerprint validation failed. Run GDS --remount.')
    raise SystemExit(1)

os.makedirs(os.path.dirname(_RESULT), exist_ok=True)
os.chdir(_CWD)
print(f'{exec_msg}: {{_CMD}}')
_t0 = time.time()
{runner}
if _r.stdout: print(_r.stdout, end='')
if _r.stderr: print(_r.stderr, end='')
_dur = time.time() - _t0

json.dump({{'command': _CMD, 'stdout': _r.stdout, 'stderr': _r.stderr,
    'returncode': _r.returncode, 'duration': _dur, 'timestamp': _TS,
    'completed': datetime.now().isoformat()
}}, open(_RESULT, 'w'), indent=2, ensure_ascii=False)

_gui_title = f'{fin_label} [{cmd_hash.upper()}]'
print(f'\\n\\033[1m{{_gui_title}}\\033[0m: {fin_msg}')
print(f'{done_marker}')
'''


def _get_gcs_translation(project_root, key, default, **kwargs):
    """Get a translated string for GDS using the logic translation dir."""
    try:
        from interface.lang import get_translation
        logic_dir = str(project_root / "tool" / "GOOGLE.GDS" / "logic")
        return get_translation(logic_dir, key, default, **kwargs)
    except Exception:
        return default.format(**kwargs) if kwargs else default


def _collapse_home(text: str) -> str:
    """Replace the expanded home directory with ~ in display text."""
    home = os.path.expanduser("~")
    if home and home != "~":
        return text.replace(home, "~")
    return text


def _classify_cdp_failure(detail: dict) -> str:
    """Classify a CDP execution failure into a reason string for Turing machine display."""
    output = (detail.get("output", "") or "").lower()
    error = (detail.get("error", "") or "").lower()
    errors = (detail.get("errors", "") or "").lower()
    combined = f"{output} {error} {errors}"

    if "not mounted" in combined or "drive not mounted" in combined:
        return "drive_not_mounted"
    if "fingerprint" in combined and "failed" in combined:
        return "mount_fingerprint_invalid"
    if "timeout" in combined or detail.get("state") == "timeout":
        return "execution_timeout"
    if "colab" in combined and "not found" in combined:
        return "colab_tab_not_found"
    if "websocket" in combined or "connection" in combined:
        return "cdp_connection_error"
    return "cdp_execution_failed"


def show_command_gui(project_root: Path, command: str, script: str, as_python: bool = False, no_capture: bool = False, done_marker: str = "", cdp_enabled: bool = False, no_feedback: bool = False):
    """
    Shows a GUI window with Copy Script and action buttons.
    When no_capture=True, the Feedback button is hidden (no result to download).
    When no_feedback=True, all action buttons are hidden (unit test mode).
    In CDP mode with no_feedback, the GUI auto-closes on success/failure.
    """
    from interface.gui import ButtonBarWindow
    import sys

    _ = lambda key, default, **kw: _get_gcs_translation(project_root, key, default, **kw)
    
    btn_copy_text = _("gui_btn_copy", "Copy Script")
    btn_copied_text = _("gui_btn_copied", "Copied!")
    btn_feedback_text = _("gui_btn_feedback", "Feedback")
    btn_finished_text = _("gui_btn_finished", "Finished")
    btn_sending_text = _("gui_btn_sending", "Sending...")

    def copy_to_clipboard():
        if sys.platform == "darwin":
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(script.encode('utf-8'))
            
    def on_copy_click(btn):
        btn.config(text=btn_copied_text, state="disabled")
        btn.after(1500, lambda: btn.config(text=btn_copy_text, state="normal"))

    def on_feedback_click(btn):
        btn.config(text=btn_sending_text, state="disabled")

    cdp_available = False
    if cdp_enabled:
        try:
            from interface.chrome import is_chrome_cdp_available as _cdp_check
            cdp_available = _cdp_check()
        except Exception:
            pass

    hide_action_buttons = no_feedback or no_capture

    if cdp_available:
        cdp_inject_timeout = 30
        buttons = [
            {
                "text": btn_copy_text,
                "cmd": copy_to_clipboard,
                "on_click": on_copy_click,
                "close_on_click": False
            },
        ]
        if not hide_action_buttons:
            buttons.append({
                "text": btn_feedback_text,
                "return_value": "Feedback",
                "cmd": None,
                "on_click": on_feedback_click,
                "close_on_click": True,
                "disable_seconds": cdp_inject_timeout
            })
    else:
        buttons = [
            {
                "text": btn_copy_text,
                "cmd": copy_to_clipboard,
                "on_click": on_copy_click,
                "close_on_click": False
            },
        ]
        if not hide_action_buttons:
            buttons.append({
                "text": btn_feedback_text,
                "return_value": "Feedback",
                "cmd": None,
                "on_click": on_feedback_click,
                "close_on_click": True,
                "disable_seconds": 30
            })
            buttons.append({
                "text": btn_finished_text,
                "return_value": "Finished",
                "cmd": None,
                "close_on_click": True,
                "disable_seconds": 30
            })
    
    # Auto-copy on startup
    copy_to_clipboard()

    cdp_thread_result = {"success": False, "attempted": False}

    def _update_gui_status(text):
        """Thread-safe GUI status update."""
        try:
            win.root.after(0, lambda: win.update_status_line(text))
        except Exception:
            pass

    def _cdp_auto_inject():
        """Background thread: inject script into Colab via Chrome DevTools Protocol."""
        try:
            from interface.chrome import is_chrome_cdp_available
            from tool.GOOGLE.interface.main import inject_and_execute, find_colab_tab
            from interface.chrome import CDPSession as _CdpSession
        except ImportError:
            return

        if not is_chrome_cdp_available():
            return

        cdp_thread_result["attempted"] = True
        _update_gui_status("[MCP] Executing command...")

        _overlay = None
        _cdp_ov = None
        try:
            from interface.cdmcp import load_cdmcp_overlay
            _overlay = load_cdmcp_overlay()
            _tab = find_colab_tab()
            if _tab and _tab.get("webSocketDebuggerUrl") and _overlay:
                _cdp_ov = _CdpSession(_tab["webSocketDebuggerUrl"], timeout=10)
                _overlay.inject_badge(_cdp_ov, text="GDS [colab]", color="#0d904f")
                _overlay.inject_focus(_cdp_ov, color="#0d904f")
                _overlay.inject_lock(_cdp_ov, base_opacity=0.08, flash_opacity=0.25,
                                      tool_name="GDS")
                _overlay.inject_highlight(_cdp_ov, ".cell.code",
                                           label="Injecting command...", color="#1a73e8")
                _overlay.increment_mcp_count(_cdp_ov, 1)
                import time as _t
                _t.sleep(0.6)
                _overlay.remove_highlight(_cdp_ov)
                _cdp_ov.close()
                _cdp_ov = None
        except Exception:
            if _cdp_ov:
                try:
                    _cdp_ov.close()
                except Exception:
                    pass
                _cdp_ov = None

        inject_code = script
        if not as_python:
            import json as _json
            inject_code = (
                "import subprocess, sys\n"
                f"_script = {_json.dumps(script)}\n"
                "_proc = subprocess.run(['bash', '-c', _script], "
                "capture_output=False, text=True)\n"
            )

        try:
            result = inject_and_execute(inject_code, timeout=300, done_marker=done_marker)
            cdp_thread_result.update(result)

            if result.get("success"):
                _update_gui_status("[MCP] Execution finished.")
                import time as _t
                _t.sleep(0.5)
                stop_file = project_root / "tmp" / f".gcs_cdp_done_{id(win)}"
                with open(stop_file, "w") as sf:
                    sf.write("Finished")
            else:
                _update_gui_status("[MCP] Execution failed. Use Feedback to report.")
                _enable_feedback_btn_via_signal()
        except Exception as e:
            cdp_thread_result["error"] = str(e)
            _update_gui_status("[MCP] Connection error. Use Feedback to report.")
            _enable_feedback_btn_via_signal()
        finally:
            if _overlay:
                try:
                    _tab = find_colab_tab()
                    if _tab and _tab.get("webSocketDebuggerUrl"):
                        _cdp_cleanup = _CdpSession(_tab["webSocketDebuggerUrl"], timeout=5)
                        _overlay.remove_all_overlays(_cdp_cleanup)
                        _cdp_cleanup.close()
                except Exception:
                    pass

    def _enable_feedback_btn_via_signal():
        """Write a signal file to tell the GUI to enable the feedback button."""
        try:
            import json as _json_sig
            signal_file = project_root / "tmp" / f".gcs_cdp_fail_{id(win)}"
            detail = {
                "error": cdp_thread_result.get("error", ""),
                "output": cdp_thread_result.get("output", ""),
                "errors": cdp_thread_result.get("errors", ""),
                "state": cdp_thread_result.get("state", ""),
            }
            with open(signal_file, "w") as sf:
                _json_sig.dump(detail, sf)
        except Exception:
            try:
                signal_file = project_root / "tmp" / f".gcs_cdp_fail_{id(win)}"
                with open(signal_file, "w") as sf:
                    sf.write("failed")
            except Exception:
                pass

    def _enable_feedback_btn():
        """Enable the Feedback button (when CDP fails, user needs manual fallback)."""
        import tkinter as tk
        try:
            main_frame = win.root.winfo_children()[0]
            for w in main_frame.winfo_children():
                if isinstance(w, tk.Frame):
                    for btn in w.winfo_children():
                        if isinstance(btn, tk.Button):
                            text = btn.cget('text')
                            if btn_feedback_text in text or 'Feedback' in text:
                                btn.config(state="normal", text=btn_feedback_text)
                                return
        except Exception:
            pass

    def _auto_close_gui():
        """Auto-close GUI when CDP execution succeeds (fallback, prefer signal file)."""
        try:
            win.finalize("success", "Finished")
        except Exception:
            pass

    def _check_cdp_done():
        """Periodically check if CDP thread wrote a done/fail signal file."""
        done_file = project_root / "tmp" / f".gcs_cdp_done_{id(win)}"
        fail_file = project_root / "tmp" / f".gcs_cdp_fail_{id(win)}"
        try:
            if done_file.exists():
                done_file.unlink(missing_ok=True)
                win.finalize("success", "Finished")
                return
            if fail_file.exists():
                import json as _json_check
                fail_detail = {}
                try:
                    with open(fail_file, "r") as ff:
                        content = ff.read().strip()
                        if content and content != "failed":
                            fail_detail = _json_check.loads(content)
                except Exception:
                    pass
                fail_file.unlink(missing_ok=True)

                if no_capture or no_feedback:
                    reason = _classify_cdp_failure(fail_detail)
                    win.finalize("error", "CDP_FAILED", reason=reason)
                else:
                    _enable_feedback_btn()
                return
        except Exception:
            pass
        try:
            win.root.after(500, _check_cdp_done)
        except Exception:
            pass

    def on_startup():
        try:
            import tkinter as tk
            main_frame = win.root.winfo_children()[0]
            button_frame = [w for w in main_frame.winfo_children() if isinstance(w, tk.Frame)][0]
            first_btn = button_frame.winfo_children()[0]
            on_copy_click(first_btn)
        except Exception:
            pass

        if cdp_available:
            import threading
            t = threading.Thread(target=_cdp_auto_inject, daemon=True)
            t.start()
            win.root.after(1000, _check_cdp_done)
        elif no_feedback:
            win.root.after(2000, lambda: win.finalize("error", "NO_CDP"))

    display_command = _collapse_home(command)
    if as_python:
        base_instruction = _("gui_instruction_copy_python",
            "Copy the script and run it in a **Python code cell** on Colab.\n\nExecuting:\n**{command}**",
            command=display_command)
    else:
        base_instruction = _("gui_instruction_copy_terminal",
            "Copy the script and run it in the **Terminal** on Colab.\n\nExecuting:\n**{command}**",
            command=display_command)

    if cdp_available:
        instruction = base_instruction + "\n\n[MCP] Connecting to Chrome with CDP..."
    else:
        instruction = base_instruction

    cmd_lines = command.count('\n') + 1
    base_height = 160 if cdp_available else 120
    extra_height = min(cmd_lines, 8) * 18
    win_height = base_height + extra_height

    if done_marker and done_marker.startswith("GDS_DONE_"):
        cmd_hash = done_marker[len("GDS_DONE_"):].upper()
    else:
        cmd_hash = hashlib.md5(command.encode()).hexdigest()[:8].upper()
    gui_title = _("gui_title_remote_command", "GDS Remote Command")
    gui_title = f"{gui_title} [{cmd_hash}]"

    gui_timeout = 120 if no_feedback else 600
    win = ButtonBarWindow(
        title=gui_title, 
        timeout=gui_timeout, 
        internal_dir=str(project_root / "tool" / "GOOGLE.GDS" / "logic"), 
        buttons=buttons,
        instruction=instruction,
        window_size=f"550x{win_height}",
        on_startup=on_startup,
        disable_auto_unlock=(cdp_available or no_feedback)
    )
    win.run()
    return win.result

if __name__ == "__main__":
    # Same subprocess pattern as remount.py
    import argparse
    import sys
    from pathlib import Path
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--command", required=True)
    parser.add_argument("--script-path", required=True)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--as-python", action="store_true")
    parser.add_argument("--no-capture", action="store_true")
    parser.add_argument("--no-feedback", action="store_true")
    parser.add_argument("--done-marker", default="")
    parser.add_argument("--cdp-enabled", action="store_true")
    args = parser.parse_args()
    
    proj_root = Path(args.project_root)
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))
    
    with open(args.script_path, 'r') as f:
        script_content = f.read()
        
    res = show_command_gui(proj_root, args.command, script_content,
                           as_python=args.as_python, no_capture=args.no_capture,
                           done_marker=args.done_marker, cdp_enabled=args.cdp_enabled,
                           no_feedback=args.no_feedback)

