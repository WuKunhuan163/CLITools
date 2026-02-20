import sys
import os
import tkinter as tk
from pathlib import Path

# Add project root to sys.path
def find_root():
    curr = Path(__file__).resolve().parent
    while curr != curr.parent:
        if (curr / "tool.json").exists() and (curr / "bin" / "TOOL").exists():
            return curr
        curr = curr.parent
    return None

project_root = find_root()
if project_root:
    root_str = str(project_root)
    if root_str in sys.path: sys.path.remove(root_str)
    sys.path.insert(0, root_str)
else:
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.tutorial.gui import TutorialWindow, TutorialStep

# Since GOOGLE.GCS contains a dot, we use relative-style imports or importlib
# Here we can use importlib to be safe
import importlib.util

def load_step_build_func(step_name):
    step_path = Path(__file__).resolve().parent / step_name / "main.py"
    spec = importlib.util.spec_from_file_location(f"gcs_step_{step_name}", str(step_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_step

def run_setup_tutorial():
    steps = [
        TutorialStep("Project Creation", load_step_build_func("step_01")),
        TutorialStep("Enable API", load_step_build_func("step_02")),
        TutorialStep("Service Account", load_step_build_func("step_03"), is_manual=True),
        TutorialStep("JSON Key", load_step_build_func("step_04"), is_manual=True),
        TutorialStep("Sharing", load_step_build_func("step_05"), is_manual=True)
    ]
    
    win = TutorialWindow(title="GCS Setup Guide", timeout=600, steps=steps, internal_dir=str(Path(__file__).resolve().parent))
    win.debug_blocks = True # Enable debug background for blocks
    win.run(win.setup_ui)
    return win.result

if __name__ == "__main__":
    run_setup_tutorial()

