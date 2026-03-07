#!/usr/bin/env python3 -u
import os
import json
import time
import base64
import hashlib
import subprocess
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

def generate_remote_command_script(project_root: Path, command: str, remote_cwd: str = "/content/drive/MyDrive/REMOTE_ROOT", as_python: bool = False, shell_type: str = "bash"):
    """
    Generates a script to be executed in Colab that runs a shell command
    and writes the result back to Google Drive.
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
    
    # We'll use a standardized path for results
    result_filename = f"result_{ts}_{cmd_hash}.json"
    
    if as_python:
        script_template = r'''# GCS Remote Command Script
import os
import sys
import subprocess
import json
import time
from datetime import datetime

cwd = %(cwd_repr)s

if not os.path.exists('/content/drive/MyDrive'):
    os.system('clear')
    print("\033[1mError\033[0m: Google Drive is not mounted.")
    sys.exit(1)

fingerprint_file = os.path.join('/content/drive/MyDrive/REMOTE_ROOT/tmp', f'.gds_mount_fingerprint_{%(mount_hash_repr)s}')
if %(mount_hash_repr)s and not os.path.exists(fingerprint_file):
    os.system('clear')
    print("\033[1mError\033[0m: Mount fingerprint validation failed.")
    sys.exit(1)

command = %(command_repr)s
result_file = os.path.join('/content/drive/MyDrive/REMOTE_ROOT/tmp', %(result_filename_repr)s)

os.makedirs(os.path.dirname(result_file), exist_ok=True)

print(f"Executing: {command}")
start_time = time.time()

try:
    process = subprocess.Popen(
        ["python3", "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=cwd
    )
    stdout, stderr = process.communicate()
    returncode = process.returncode
except Exception as e:
    stdout = ""
    stderr = str(e)
    returncode = -1

duration = time.time() - start_time

result_data = {
    "command": command,
    "stdout": stdout,
    "stderr": stderr,
    "returncode": returncode,
    "duration": duration,
    "timestamp": %(ts_repr)s,
    "completed": datetime.now().isoformat()
}

with open(result_file, 'w') as f:
    json.dump(result_data, f, indent=2)

print("\033[1mFinished\033[0m: Execution completed and result saved. You may now press the Finished button.")
''' % {
            'command_repr': repr(command),
            'cwd_repr': repr(remote_cwd),
            'result_filename_repr': repr(result_filename),
            'ts_repr': repr(ts),
            'mount_hash_repr': repr(mount_hash)
        }
    else:
        # Bash version: write a self-contained script to /tmp then execute it.
        # This avoids nested heredoc issues when pasting into Colab terminals.
        import shlex
        script_id = f"{ts}_{cmd_hash}"
        
        # Inner script body (written to a file, then executed)
        inner_script = f'''#!/bin/bash
if [ ! -d "/content/drive/MyDrive" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Google Drive is not mounted. Run '\\033[1mGCS --remount\\033[0m' locally first."
    exit 1
fi

if [ -n "{mount_hash}" ] && [ ! -f "/content/drive/MyDrive/REMOTE_ROOT/tmp/.gds_mount_fingerprint_{mount_hash}" ]; then
    clear
    echo -e "\\033[1mError\\033[0m: Mount fingerprint validation failed. Run '\\033[1mGCS --remount\\033[0m' locally to resync."
    exit 1
fi

mkdir -p "{remote_cwd}"
cd "{remote_cwd}"

OUTPUT_FILE="/tmp/gcs_stdout_{script_id}"
ERROR_FILE="/tmp/gcs_stderr_{script_id}"
RESULT_BASE="/content/drive/MyDrive/REMOTE_ROOT/tmp"
mkdir -p "$RESULT_BASE"
RESULT_FILE="$RESULT_BASE/{result_filename}"

echo "Executing command..."

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

export GCS_EXIT_CODE=$EXIT_CODE
export GCS_TIMESTAMP="{ts}"
export GCS_COMMAND={shlex.quote(command)}
export GCS_RESULT_FILE="$RESULT_FILE"
export GCS_STDOUT_FILE="$OUTPUT_FILE"
export GCS_STDERR_FILE="$ERROR_FILE"

python3 -c '
import json, os
from datetime import datetime
sf = os.environ["GCS_STDOUT_FILE"]
ef = os.environ["GCS_STDERR_FILE"]
so = open(sf, "r", errors="ignore").read() if os.path.exists(sf) else ""
se = open(ef, "r", errors="ignore").read() if os.path.exists(ef) else ""
r = {{"command": os.environ["GCS_COMMAND"], "stdout": so, "stderr": se, "returncode": int(os.environ["GCS_EXIT_CODE"]), "duration": 0, "timestamp": os.environ["GCS_TIMESTAMP"], "completed": datetime.now().isoformat()}}
with open(os.environ["GCS_RESULT_FILE"], "w") as f: json.dump(r, f, indent=2, ensure_ascii=False)
'

rm -f "$OUTPUT_FILE" "$ERROR_FILE"
clear
echo -e "\\033[1mFinished\\033[0m: Execution completed and result saved. You may now press the Finished button."
'''

        # Wrap in a cat-heredoc-then-execute pattern for safe terminal pasting
        script_template = f'''cat > /tmp/gcs_run_{script_id}.sh << 'GCS_SCRIPT_EOF'
{inner_script}GCS_SCRIPT_EOF
bash /tmp/gcs_run_{script_id}.sh ; rm -f /tmp/gcs_run_{script_id}.sh'''

    return script_template, {
        "ts": ts,
        "hash": cmd_hash,
        "result_filename": result_filename
    }

def show_command_gui(project_root: Path, command: str, script: str, as_python: bool = False):
    """
    Shows a 3-button window: Copy Script, Direct Feedback, Finished.
    """
    from logic.gui.tkinter.blueprint.button_bar.gui import ButtonBarWindow
    import sys
    
    def copy_to_clipboard():
        if sys.platform == "darwin":
            process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
            process.communicate(script.encode('utf-8'))
            
    def on_copy_click(btn):
        old_text = btn.cget("text")
        btn.config(text="Copied!", state="disabled")
        btn.after(1500, lambda: btn.config(text=old_text, state="normal"))

    def on_feedback_click(btn):
        btn.config(text="Sending...", state="disabled")

    buttons = [
        {
            "text": "Copy Script", 
            "cmd": copy_to_clipboard, 
            "on_click": on_copy_click,
            "close_on_click": False
        },
        {
            "text": "Feedback", 
            "cmd": None, 
            "on_click": on_feedback_click,
            "close_on_click": True,
            "disable_seconds": 5
        },
        {
            "text": "Finished", 
            "cmd": None, 
            "close_on_click": True,
            "disable_seconds": 5
        }
    ]
    
    # Auto-copy on startup
    copy_to_clipboard()
    
    def on_startup():
        try:
            # First frame is main_frame, second frame inside it is button_frame
            main_frame = win.root.winfo_children()[0]
            button_frame = [w for w in main_frame.winfo_children() if isinstance(w, tk.Frame)][0]
            first_btn = button_frame.winfo_children()[0]
            on_copy_click(first_btn)
        except Exception:
            pass

    cell_type = "a **Python code cell**" if as_python else "the **Terminal**"
    instruction = f"Copy the script and run it in {cell_type} on Colab.\n\nExecuting:\n**{command}**"

    cmd_lines = command.count('\n') + 1
    base_height = 120
    extra_height = min(cmd_lines, 8) * 18
    win_height = base_height + extra_height

    win = ButtonBarWindow(
        title="GCS Remote Command", 
        timeout=600, 
        internal_dir=str(project_root / "tool" / "GOOGLE.GCS" / "logic"), 
        buttons=buttons,
        instruction=instruction,
        window_size=f"550x{win_height}",
        on_startup=on_startup
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
    args = parser.parse_args()
    
    proj_root = Path(args.project_root)
    if str(proj_root) not in sys.path:
        sys.path.insert(0, str(proj_root))
    
    with open(args.script_path, 'r') as f:
        script_content = f.read()
        
    res = show_command_gui(proj_root, args.command, script_content, as_python=args.as_python)

