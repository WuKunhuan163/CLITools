#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DUMMY Tool - Verification for Unified GUI Interface
"""

import os
import sys
import argparse
import tempfile
import json
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.tool.base import ToolBase
from logic.config import get_color

class DummyTool(ToolBase):
    def __init__(self):
        super().__init__("DUMMY")

def get_dummy_gui(timeout=300, custom_id=None):
    tool = DummyTool()
    # Use system python or PYTHON tool if available
    python_exe = sys.executable
    try:
        from tool.USERINPUT.main import UserInputTool
        python_exe = UserInputTool().get_python_exe()
    except: pass

    tkinter_script = r'''
import os
import sys
import json
import tkinter as tk
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

class DummyWindow(BaseGUIWindow):
    def __init__(self, title, timeout):
        super().__init__(title, timeout, Path(%(internal_dir)r), tool_name="DUMMY")
        self.entry = None

    def get_current_state(self):
        return self.entry.get() if self.entry else None

    def setup_ui(self):
        setup_gui_environment()
        self.root.geometry("400x200")
        
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text="Verify",
            submit_cmd=lambda: self.finalize("success", self.get_current_state())
        )

        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="Unified GUI Interface Verification", font=get_label_style()).pack(pady=(0, 10))
        tk.Label(main_frame, text="Enter something to test partial capture:").pack(pady=(0, 5))
        
        self.entry = tk.Entry(main_frame, font=get_label_style())
        self.entry.pack(fill=tk.X)
        self.entry.focus_set()
        
        self.start_timer(self.status_label)

if __name__ == "__main__":
    win = DummyWindow("DUMMY Verification", %(timeout)d)
    win.run(win.setup_ui, custom_id=%(custom_id)r)
''' % {
        'project_root': str(tool.project_root),
        'internal_dir': str(tool.script_dir / "logic"),
        'timeout': timeout,
        'custom_id': custom_id
    }

    with tempfile.NamedTemporaryFile(mode='w', prefix='DUMMY_gui_', suffix='.py', delete=False) as tmp:
        tmp.write(tkinter_script)
        tmp_path = tmp.name

    try:
        return tool.run_gui(python_exe, tmp_path, timeout, custom_id)
    finally:
        if os.path.exists(tmp_path): os.remove(tmp_path)

def main():
    tool = DummyTool()
    if tool.handle_command_line(): return
    
    parser = argparse.ArgumentParser(description="DUMMY Tool")
    parser.add_argument('command', nargs='?', help="Command to run (stop, submit, cancel)")
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--id', type=str)
    args, unknown = parser.parse_known_args()
    
    # Standard remote commands
    if args.command in ["stop", "submit", "cancel", "add_time"]:
        from logic.gui.manager import handle_gui_remote_command
        return handle_gui_remote_command("DUMMY", tool.project_root, args.command, unknown, tool.get_translation)

    result = get_dummy_gui(timeout=args.timeout, custom_id=args.id)
    
    BOLD, GREEN, RED, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RED"), get_color("RESET")
    
    if result['status'] == 'success':
        print(f"{BOLD}{GREEN}Result{RESET}: {result['data']}")
    elif result['status'] == 'terminated':
        label = tool.get_translation("label_terminated", "Terminated")
        reason = result.get('reason', 'unknown')
        data = result.get('data')
        
        # Human readable reasons
        reason_map = {
            "stop": tool.get_translation("msg_terminated_external", "Instance terminated from external signal"),
            "interrupted": tool.get_translation("msg_interrupted", "Interrupted by user"),
            "signal": tool.get_translation("msg_terminated_external", "Instance terminated from external signal")
        }
        reason_text = reason_map.get(reason, reason)
        
        msg = f"{BOLD}{RED}{label}{RESET}: {reason_text}"
        if data:
            msg += f" - Partial Input: {data}"
        print(msg)
    else:
        label_error = tool.get_translation("label_error", "Error")
        print(f"{BOLD}{RED}{label_error}{RESET}: {result['status']} - {result.get('message', 'No message')}")

if __name__ == "__main__":
    main()
