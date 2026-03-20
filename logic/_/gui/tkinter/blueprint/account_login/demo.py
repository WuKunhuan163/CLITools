import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/account_login/demo.py -> 6 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic._.gui.tkinter.blueprint.account_login.gui import AccountLoginWindow

if __name__ == "__main__":
    from logic._.gui.engine import setup_gui_environment, get_safe_python_for_gui
    from logic.base.blueprint.base import ToolBase
    from logic._.utils.turing.models.progress import ProgressTuringMachine
    from logic._.utils.turing.logic import TuringStage
    from logic._.config import get_color
    import subprocess
    import os

    # 1. Parent Process Logic (Manager)
    if os.environ.get("GDS_GUI_MANAGED") != "1":
        def run_parent():
            tool = ToolBase("LOGIN_DEMO")
            py_exe = sys.executable
            
            BOLD, GREEN, RESET = get_color("BOLD"), get_color("GREEN"), get_color("RESET")
            final_res = {}

            def demo_action(stage=None):
                nonlocal final_res
                # Set environment to indicate managed mode for the child
                env = os.environ.copy()
                env["GDS_GUI_MANAGED"] = "1"
                # Re-run this same script as a managed subprocess
                final_res = tool.run_gui(py_exe, __file__, timeout=60)
                return final_res.get("status") == "success"

            pm = ProgressTuringMachine(project_root=tool.project_root, tool_name="DEMO")
            pm.add_stage(TuringStage(
                "interaction", demo_action,
                active_status="Waiting for demo feedback",
                active_name="via GUI",
                success_status="Received",
                success_name="demo feedback",
                fail_status="Failed to receive",
                fail_name="demo feedback"
            ))
            
            # Use ephemeral=True and final_newline=False to completely erase without blank line
            if pm.run(ephemeral=True, final_msg="", final_newline=False):
                sys.stdout.write(f"\r\033[K{BOLD}{GREEN}Successfully received{RESET}: {final_res.get('data')}\n")
                sys.stdout.flush()
        
        run_parent()
        sys.exit(0)

    # 2. Child Process Logic (Actual GUI)
    # Auto-reexecute with safe python if current one lacks tkinter
    try:
        import _tkinter
    except ImportError:
        py_exe = get_safe_python_for_gui()
        if py_exe and py_exe != sys.executable:
            env = os.environ.copy()
            env["PYTHONPATH"] = str(project_root)
            sys.exit(subprocess.call([py_exe, __file__], env=env))
        else:
            sys.exit("Error: Tkinter not found and no safe Python alternative discovered.")

    setup_gui_environment()
    
    # Custom labels for the demo
    win = AccountLoginWindow(
        title="Account Login Demo",
        timeout=60,
        internal_dir=str(project_root / "logic" / "gui"),
        instruction_text="Demo Login Interface",
        account_label="Username:",
        password_label="Password:",
        error_msg="This is a demo error message shown on launch."
    )
    
    win.run(win.setup_ui)

