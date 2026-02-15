import sys
from pathlib import Path
import tkinter as tk

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/tutorial/demo.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.tutorial.gui import TutorialWindow, TutorialStep
from logic.gui.tkinter.style import get_label_style, get_gui_colors

def build_step_1(frame, win):
    tk.Label(frame, text="Welcome to the Tutorial", font=("Arial", 16, "bold")).pack(pady=(40, 10))
    tk.Label(frame, text="This is the first step of the demonstration.\n\nEverything looks good! Click 'Next' to continue.", 
             font=get_label_style(), wraplength=500, justify="center").pack(pady=10)

def build_step_2(frame, win):
    tk.Label(frame, text="Final Verification", font=("Arial", 16, "bold")).pack(pady=(40, 10))
    tk.Label(frame, text="To complete this tutorial, please enter the code '123456'.", 
             font=get_label_style(), wraplength=500, justify="center").pack(pady=(0, 30))
    
    code_frame = tk.Frame(frame)
    code_frame.pack()
    
    win.demo_code_vars = []
    win.demo_entries = []
    
    allowed = "0123456789"
    n = 6
    
    def on_key(event, idx):
        char = event.char
        if char in allowed and char != "":
            win.demo_code_vars[idx].set(char)
            if idx < n - 1:
                win.demo_entries[idx + 1].focus_set()
            return "break"
        if event.keysym == "BackSpace":
            if win.demo_code_vars[idx].get() == "":
                if idx > 0:
                    win.demo_entries[idx - 1].focus_set()
                    win.demo_code_vars[idx - 1].set("")
            else:
                win.demo_code_vars[idx].set("")
            return "break"
        if event.keysym in ["Left", "Right", "Tab"]:
            return None
        return "break"

    for i in range(n):
        var = tk.StringVar()
        win.demo_code_vars.append(var)
        entry = tk.Entry(code_frame, textvariable=var, width=2, font=("Arial", 24, "bold"),
                         justify='center', relief=tk.RIDGE, borderwidth=2, insertontime=0)
        entry.pack(side=tk.LEFT, padx=5)
        entry.bind("<KeyPress>", lambda e, idx=i: on_key(e, idx))
        win.demo_entries.append(entry)
    
    win.demo_entries[0].focus_set()

def validate_step_2(win):
    if not hasattr(win, "demo_code_vars"): return False
    code = "".join([v.get() for v in win.demo_code_vars])
    if code == "123456":
        return True
    else:
        win.show_error("Invalid code. Please enter '123456' to complete.")
        return False

def run_demo():
    from logic.gui.engine import setup_gui_environment
    setup_gui_environment()
    
    # We define steps first, but validation needs 'win'. 
    # We can pass 'win' to validate_func if we change the blueprint slightly, 
    # or just use a lambda that captures the variable.
    
    steps = [
        TutorialStep("Welcome", build_step_1),
        TutorialStep("Verify", build_step_2, validate_func=lambda: validate_step_2(demo_win))
    ]
    
    global demo_win
    demo_win = TutorialWindow(
        title="Tutorial Blueprint Demo",
        timeout=600,
        internal_dir=str(script_path.parent),
        steps=steps
    )
    
    demo_win.run(demo_win.setup_ui)
    
    # Print result for verification
    import json
    print(f"\nDEMO_RESULT:{json.dumps(demo_win.result)}")

if __name__ == "__main__":
    run_demo()

