#!/usr/bin/env python3
import sys
from pathlib import Path

def get_icloud_interface():
    """Returns a stable interface for iCloud functionalities."""
    # Robust project root detection
    script_path = Path(__file__).resolve()
    curr = script_path.parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin").exists():
            project_root = curr
            break
        curr = curr.parent
    else:
        project_root = None

    def run_login_gui(timeout=300, apple_id=None, error_msg=None):
        from logic.gui.manager import run_gui_subprocess
        from logic.tool.base import ToolBase
        import os
        
        # We need a tool instance for the manager
        tool = ToolBase("iCloud")
        
        # Path to the login GUI script
        gui_script = str(script_path.parent.parent / "gui" / "login.py")
        
        # Build arguments for the script if it were run via CLI
        os.environ["GDS_LOGIN_APPLE_ID"] = apple_id or ""
        os.environ["GDS_LOGIN_ERROR"] = error_msg or ""
        
        # Using sys.executable to ensure same environment
        res = run_gui_subprocess(tool, sys.executable, gui_script, timeout)
        return res

    return {
        "run_login_gui": run_login_gui
    }

