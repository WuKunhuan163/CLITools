import os
import sys
import subprocess
import platform
from pathlib import Path

def is_sandboxed():
    """Check if we are likely running in a sandbox environment (like Cursor terminal)."""
    # 1. Cursor specific (macOS Seatbelt)
    if os.environ.get('CURSOR_SANDBOX') == 'seatbelt':
        return True
    if os.environ.get('__CFBundleIdentifier') == 'com.todesktop.230313mzl4w4u92':
        return True
    
    # 2. General Darwin (macOS)
    if platform.system() == 'Darwin':
        if os.environ.get('TERM') == 'dumb':
            return True
            
    # 3. Linux (check for common sandbox markers or missing display)
    if platform.system() == 'Linux':
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            return True
        if os.path.exists('/.dockerenv'): # Docker is a form of sandbox
            return True
            
    # 4. Windows
    if platform.system() == 'Windows':
        # Integrity levels or other markers could be checked here
        pass
        
    return False

def get_sandbox_type():
    """Identify the specific type of sandbox for better error messaging."""
    if os.environ.get('CURSOR_SANDBOX') == 'seatbelt':
        return "macOS Seatbelt (Cursor)"
    if os.environ.get('__CFBundleIdentifier') == 'com.todesktop.230313mzl4w4u92':
        return "macOS Seatbelt (Cursor)"
    
    if platform.system() == 'Darwin':
        if os.environ.get('TERM') == 'dumb':
            return "Restricted Terminal (macOS)"
            
    if platform.system() == 'Linux':
        if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
            return "No Display (Linux)"
        if os.path.exists('/.dockerenv'):
            return "Docker Container"
            
    return "Unknown Sandbox"

def get_safe_python_for_gui():
    """
    Returns a Python executable path that is known to work with GUI in the current environment.
    """
    # Prioritize the Python tool's version as requested by the user
    # Specifically version 3.10.19 which supports tkinter
    version = "python3.10.19"
    project_root = Path(__file__).resolve().parent.parent
    
    # Same logic as USERINPUT for flexibility
    system_tag = "macos"
    if sys.platform == "linux": system_tag = "linux64"
    elif sys.platform == "win32": system_tag = "windows-amd64"

    possible_dirs = [version, f"{version}-{system_tag}", f"{version}-macos", f"{version}-linux64"]
    
    # Try to use centralized config from PYTHON tool
    try:
        sys.path.append(str(project_root / "tool" / "PYTHON" / "logic"))
        from config import INSTALL_DIR
        install_root = INSTALL_DIR
    except ImportError:
        # Fallback path if config not available
        install_root = project_root / "tool" / "PYTHON" / "data" / "install"
    
    for d in possible_dirs:
        python_exec = install_root / d / "install" / "bin" / "python3"
        if python_exec.exists(): return str(python_exec)
        python_exec_win = install_root / d / "install" / "python.exe"
        if python_exec_win.exists(): return str(python_exec_win)
    
    # Try importing from PYTHON tool utilities if available
    python_utils = project_root / "tool" / "PYTHON" / "logic" / "utils.py"
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
        
        # NSInternalInconsistencyException: aString != nil fix
        # Ensure sys.argv[0] is not empty as it's used for app name
        if not sys.argv or not sys.argv[0] or sys.argv[0] == '-c':
            sys.argv = [prog_name] + sys.argv[1:] if sys.argv else [prog_name]

        # Spoofing bundle ID can help with HiDPI scaling and display restrictions
        if is_sandboxed() or '__CFBundleIdentifier' not in os.environ:
            os.environ['__CFBundleIdentifier'] = 'com.apple.Safari'
            
    # Add other platforms if needed
    pass

