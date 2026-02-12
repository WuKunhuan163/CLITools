import sys
import tkinter as tk
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/timed_bottom_bar/demo.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
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
        self.root.geometry("400x200")
        self.status_label = setup_common_bottom_bar(
            self.root, self, 
            submit_text="Close", 
            submit_cmd=lambda: self.finalize("success", "manual_close")
        )
        
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Centered text box as requested
        text_widget = tk.Text(main_frame, height=3, font=get_label_style(), bg="#f0f0f0", relief=tk.FLAT)
        text_widget.pack(fill=tk.BOTH, expand=True)
        text_widget.insert(tk.END, "This window will automatically close in 10 seconds.")
        text_widget.tag_configure("center", justify='center')
        text_widget.tag_add("center", "1.0", "end")
        text_widget.config(state=tk.DISABLED)

        self.start_timer(self.status_label)

if __name__ == "__main__":
    from logic.gui.engine import setup_gui_environment, get_safe_python_for_gui
    import subprocess
    import os

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

