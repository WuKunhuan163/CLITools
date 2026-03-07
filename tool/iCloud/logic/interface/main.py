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
        
        os.environ["GDS_LOGIN_APPLE_ID"] = apple_id or ""
        os.environ["GDS_LOGIN_ERROR"] = error_msg or ""
        
        # Pass canonical session directory so the GUI uses the same path as main.py
        session_dir = project_root / "tool" / "iCloud.iCloudPD" / "data" / "session"
        os.environ["GDS_LOGIN_SESSION_DIR"] = str(session_dir)
        
        auth_label = tool.get_translation(
            "label_waiting_auth_full",
            "Waiting for iCloud authentication via GUI"
        )
        res = run_gui_subprocess(tool, sys.executable, gui_script, timeout, waiting_label=auth_label)
        return res

    return {
        "run_login_gui": run_login_gui
    }

