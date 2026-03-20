import os
import sys
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
    # 1. Try to use the PYTHON tool's interface first
    # logic/gui/engine.py -> 3 levels up to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    python_tool_interface = project_root / "tool" / "PYTHON" / "interface" / "main.py"
    
    if python_tool_interface.exists():
        try:
            sys.path.append(str(project_root))
            from tool.PYTHON.interface.main import get_python_exe_func
            get_python_exe = get_python_exe_func()
            # Request version 3.10.19 which is known to have tkinter in this ecosystem
            py_exe = get_python_exe("3.10.19")
            if py_exe and os.path.exists(py_exe):
                return str(py_exe)
        except Exception:
            pass

    # 2. Fallback to manual detection (same as before)
    version = "3.10.19"
    system_tag = "macos"
    if sys.platform == "linux": system_tag = "linux64"
    elif sys.platform == "win32": system_tag = "windows-amd64"

    # Support both with and without 'python' prefix
    possible_versions = [version, f"python{version}"]
    possible_suffixes = ["", f"-{system_tag}", "-macos", "-linux64", "-macos-arm64"]
    
    install_root = project_root / "tool" / "PYTHON" / "data" / "install"
    
    for v in possible_versions:
        for s in possible_suffixes:
            d = f"{v}{s}"
            python_exec = install_root / d / "install" / "bin" / "python3"
            if python_exec.exists(): return str(python_exec)
            python_exec_win = install_root / d / "install" / "python.exe"
            if python_exec_win.exists(): return str(python_exec_win)
    
    # 3. Darwin specific system fallbacks
    if platform.system() == "Darwin":
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

def play_notification_bell(project_root: Path):
    """Unified interface to play the notification bell."""
    import subprocess
    import threading
    bell_path = project_root / "logic" / "utils" / "asset" / "audio" / "bell.mp3"
    
    def run_play():
        try:
            if bell_path.exists():
                if platform.system() == "Darwin":
                    subprocess.run(["afplay", str(bell_path)], stderr=subprocess.DEVNULL, timeout=5)
                elif platform.system() == "Linux":
                    subprocess.run(["aplay", str(bell_path)], stderr=subprocess.DEVNULL, timeout=5)
                elif platform.system() == "Windows":
                    import winsound
                    winsound.PlaySound(str(bell_path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                play_system_alert()
        except: pass
    threading.Thread(target=run_play, daemon=True).start()

def play_system_alert():
    """Plays a default system alert sound as a fallback."""
    import subprocess
    try:
        if platform.system() == "Darwin":
            system_sound = "/System/Library/Sounds/Glass.aiff"
            if os.path.exists(system_sound):
                subprocess.run(["afplay", system_sound], stderr=subprocess.DEVNULL, timeout=5)
        elif platform.system() == "Windows":
            import winsound
            # SystemAsterisk is a standard Windows event sound
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        elif platform.system() == "Linux":
            subprocess.run(["beep"], stderr=subprocess.DEVNULL, timeout=2)
    except:
        pass


