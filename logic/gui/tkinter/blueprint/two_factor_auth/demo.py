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
            sys.exit(subprocess.call([py_exe, __file__] + sys.argv[1:], env=env))
        else:
            sys.exit("Error: Tkinter not found and no safe Python alternative discovered.")

    setup_gui_environment()
    
    # Showcase 6-digit 2FA
    win = TwoFactorAuthWindow(
        title="2FA Verification Demo",
        timeout=120,
        internal_dir=str(project_root / "logic" / "gui"),
        n=6
    )
    
    win.run(win.setup_ui)

