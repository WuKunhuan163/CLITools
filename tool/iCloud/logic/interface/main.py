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

    def run_login_gui(timeout=300):
        from tool.iCloud.logic.gui.login import ICloudLoginWindow
        from logic.gui.engine import setup_gui_environment
        
        setup_gui_environment()
        
        internal_dir = str(script_path.parent.parent)
        win = ICloudLoginWindow(
            title="iCloud Login",
            timeout=timeout,
            internal_dir=internal_dir
        )
        # Setup UI and run
        win.run(win.setup_ui)
        return win.result

    return {
        "run_login_gui": run_login_gui
    }

