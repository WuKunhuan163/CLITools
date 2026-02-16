import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/timed_bottom_bar/demo.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
# Actually it should be 5 levels to reach project root if logic is the first level
# Wait: demo.py(0) -> timed_bottom_bar(1) -> blueprint(2) -> tkinter(3) -> gui(4) -> logic(5) -> ROOT(6)
project_root = script_path.parent.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.timed_bottom_bar.gui import BaseGUIWindow, setup_common_bottom_bar
from logic.gui.tkinter.style import get_label_style

class DemoWindow(BaseGUIWindow):
    def __init__(self, title, timeout):
        # Using root logic directory for translations in demo
        internal_dir = str(project_root / "logic" / "gui")
        super().__init__(title, timeout, internal_dir, tool_name="DEMO")

    def get_current_state(self):
        return "Demo data"

    def setup_ui(self):
        import tkinter as tk
        self.root.geometry("400x200")
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text="Close", 
            submit_cmd=lambda: self.finalize("success", "manual_close")
        )
        
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Centered text box
        text_widget = tk.Text(main_frame, height=3, font=get_label_style(), bg="#f0f0f0", relief=tk.FLAT)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, "This window will automatically close in 10 seconds.")
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("center", "1.0", "end")
        text_widget.config(state=tk.DISABLED)

        self.start_timer(self.status_label)

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
            tool = ToolBase("BAR_DEMO")
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
    
    win = DemoWindow("Timed Bottom Bar Demo", 10)
    win.run(win.setup_ui)

