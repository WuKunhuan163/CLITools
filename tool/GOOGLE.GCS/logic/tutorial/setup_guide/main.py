import sys
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

from interface.gui import TutorialWindow, TutorialStep
from interface.lang import get_translation

import importlib.util

_LOGIC_DIR = str(Path(__file__).resolve().parent.parent.parent)

def _(key, default, **kwargs):
    return get_translation(_LOGIC_DIR, key, default, **kwargs)

def load_step_build_func(step_name):
    step_path = Path(__file__).resolve().parent / step_name / "main.py"
    spec = importlib.util.spec_from_file_location(f"gcs_step_{step_name}", str(step_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.build_step

def run_setup_tutorial(on_step_change=None):
    steps = [
        TutorialStep(_("tutorial_project_creation", "Project Creation"), load_step_build_func("step_01")),
        TutorialStep(_("tutorial_enable_api", "Enable API"), load_step_build_func("step_02")),
        TutorialStep(_("tutorial_service_account", "Service Account"), load_step_build_func("step_03")),
        TutorialStep(_("tutorial_json_key", "JSON Key"), load_step_build_func("step_04")),
        TutorialStep(_("tutorial_folder_setup", "Folder Setup"), load_step_build_func("step_05")),
        TutorialStep(_("tutorial_remote_notebook", "Remote Notebook"), load_step_build_func("step_06"))
    ]
    
    win = TutorialWindow(
        title=_("tutorial_window_title", "GCS Setup Guide"), timeout=600, steps=steps,
        internal_dir=str(Path(__file__).resolve().parent),
        on_step_change=on_step_change
    )
    win.run(win.setup_ui)
    return win.result

if __name__ == "__main__":
    run_setup_tutorial()

