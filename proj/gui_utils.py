import os
import sys
import subprocess
import platform
from pathlib import Path

def is_sandboxed():
    """Check if we are likely running in a sandbox environment (like Cursor terminal)."""
    # Check for Cursor bundle ID
    if os.environ.get('__CFBundleIdentifier') == 'com.todesktop.230313mzl4w4u92':
        return True
    
    # Check for restricted environment variables
    if os.environ.get('TERM') == 'dumb' and platform.system() == 'Darwin':
        return True
        
    return False

def get_safe_python_for_gui():
    """
    Returns a Python executable path that is known to work with GUI in the current environment.
    """
    # Prioritize the Python tool's version as requested by the user
    # Specifically version 3.10.19 which supports tkinter
    version = "python3.10.19"
    project_root = Path(__file__).resolve().parent.parent
    python_exec = project_root / "tool" / "PYTHON" / "proj" / "install" / version / "install" / "bin" / "python3"
    
    if python_exec.exists():
        return str(python_exec)
    
    # Try importing from PYTHON tool utilities if available
    python_utils = project_root / "tool" / "PYTHON" / "proj" / "utils.py"
    if python_utils.exists():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("python_utils", str(python_utils))
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.get_python_exec(version)
        except Exception:
            pass

    if platform.system() == "Darwin":
        # Check system paths as a very last resort, though user warned against it
        for py in ["/usr/local/bin/python3", "/usr/bin/python3"]:
            if os.path.exists(py):
                return py
                
    return sys.executable

def setup_gui_environment():
    """
    Configure environment variables to help GUI applications run more reliably
    in restricted or sandboxed environments.
    """
    if platform.system() == "Darwin":
        # Set a reasonable app name
        prog_name = "USERINPUT"
        os.environ['RESOURCE_NAME'] = prog_name
        os.environ['TK_APP_NAME'] = prog_name
        
        # Spoofing bundle ID can sometimes cause issues in newer macOS sandboxes
        # if the spoofed ID doesn't match the actual process signature.
        # if is_sandboxed():
        #     os.environ['__CFBundleIdentifier'] = 'com.apple.Terminal'
            
    # Add other platforms if needed
    pass

