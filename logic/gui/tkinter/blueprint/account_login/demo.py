import sys
from pathlib import Path

# Add project root to sys.path
script_path = Path(__file__).resolve()
# logic/gui/tkinter/blueprint/account_login/demo.py -> 5 levels up to project root
project_root = script_path.parent.parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from logic.gui.tkinter.blueprint.account_login.gui import AccountLoginWindow

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
    
    # Custom labels for the demo
    win = AccountLoginWindow(
        title="Account Login Demo",
        timeout=60,
        internal_dir=str(project_root / "logic" / "gui"),
        instruction_text="Demo Login Interface",
        account_label="Email:",
        password_label="Access Key:"
    )
    
    win.run(win.setup_ui)

