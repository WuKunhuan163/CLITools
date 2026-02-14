import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/two_factor_auth/demo.py -> 6 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.two_factor_auth.gui import TwoFactorAuthWindow

if __name__ == "__main__":
    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui
    from logic.tool.base import ToolBase
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.config import get_color
    import subprocess
    import os

    # 1. Parent Process Logic (Manager)
    if os.environ.get("GDS_GUI_MANAGED") != "1":
        def run_parent():
            tool = ToolBase("2FA_DEMO")
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
                success_name="demo feedback"
            ))
            
            # Use ephemeral=True and an empty final_msg to completely erase the stage line
            if pm.run(ephemeral=True, final_msg=""):
                print(f"{BOLD}{GREEN}Successfully received{RESET}: {final_res.get('data')}")
        
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
            sys.exit(subprocess.call([py_exe, __file__] + sys.argv[1:], env=env))
        else:
            sys.exit("Error: Tkinter not found and no safe Python alternative discovered.")

    setup_gui_environment()
    
    def demo_verify_handler(code):
        import time
        time.sleep(1) # Simulate network delay
        if code == "122222":
            return {"status": "error", "message": "Invalid 2FA code (Simulated error for 122222)."}
        return {"status": "success", "data": code}

    # Showcase 6-digit 2FA
    win = TwoFactorAuthWindow(
        title="2FA Verification Demo",
        timeout=120,
        internal_dir=str(project_root / "logic" / "gui"),
        n=6,
        prompt_msg="Hint: Please enter 123456 to simulate verification. 122222 will fail.",
        verify_handler=demo_verify_handler
    )
    
    win.run(win.setup_ui)
