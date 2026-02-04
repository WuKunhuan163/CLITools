import os
import sys
import platform
import subprocess
import json
import time
import re
from pathlib import Path

# Try to import shared utils for translation
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent.parent

try:
    from logic_internal.lang.utils import get_translation
except ImportError:
    def get_translation(d, k, default): return default

try:
    from .config import INSTALL_DIR
except ImportError:
    # Fallback if config is not available
    INSTALL_DIR = script_dir.parent / "data" / "install"

def _(key, default, **kwargs):
    text = get_translation(str(script_dir), key, default)
    return text.format(**kwargs)

def get_system_tag():
    system = sys.platform
    machine = platform.machine().lower()
    if system == "darwin":
        return "macos-arm64" if "arm" in machine or "aarch64" in machine else "macos"
    if system == "linux":
        try:
            out = subprocess.run(["ldd", "--version"], capture_output=True, text=True).stderr
            if "musl" in out.lower(): return "linux64-musl"
        except: pass
        return "linux64"
    if system == "win32":
        if "arm" in machine: return "windows-arm64"
        return "windows-amd64" if "64" in machine else "windows-x86"
    return "unknown"

class MultiLineManager:
    """Manages multiple erasable lines for parallel workers."""
    def __init__(self, initial_count=0):
        self.worker_lines = {} # worker_id -> (last_text, line_index)
        self.total_lines = initial_count
        self._initialized = False

    def register_worker(self, worker_id):
        if worker_id not in self.worker_lines:
            line_idx = len(self.worker_lines)
            self.worker_lines[worker_id] = ("", line_idx)
            # Print an empty line to reserve space
            print("")
            self.total_lines += 1

    def update(self, worker_id, text):
        if worker_id not in self.worker_lines:
            self.register_worker(worker_id)
        
        last_text, line_idx = self.worker_lines[worker_id]
        if last_text == text: return
        
        self.worker_lines[worker_id] = (text, line_idx)
        
        # Calculate how many lines to move up
        up_count = self.total_lines - line_idx
        
        # ANSI: \033[F moves to start of previous line
        # We use \033[A (up) and \r (start of line)
        sys.stdout.write(f"\033[{up_count}A\r\033[K{text}\033[{up_count}B\r")
        sys.stdout.flush()

    def finalize(self):
        """Move cursor below all managed lines."""
        # The cursor is already at the bottom because each update moves it back down
        pass

def regularize_version_name(version, platform=None):
    """
    Standardize version name to 'X.Y.Z-platform'.
    If platform is not provided, it uses the system tag.
    """
    if version.startswith("python"):
        version = version[6:]
    
    # Extract version part if it already has a hyphen
    if "-" in version:
        version = version.split("-")[0]
        
    tag = platform or get_system_tag()
    return f"{version}-{tag}"

def run_with_progress(cmd, prefix, worker_id=None, manager=None, interval=0.5):
    """
    Runs a command and parses its stderr for percentage progress.
    Updates an erasable line (via sys.stdout.write or MultiLineManager).
    """
    # Force progress output for curl and git if possible
    if cmd[0] == "curl":
        if "-#" not in cmd and "--progress-bar" not in cmd:
            cmd.insert(1, "-#")
    elif "git" in cmd[0] and "push" in cmd:
        if "--progress" not in cmd:
            cmd.append("--progress")

    # Initial progress display
    initial_text = f"{prefix}: 0%"
    if manager and worker_id:
        manager.update(worker_id, initial_text)
    else:
        sys.stdout.write(f"\r\033[K{initial_text}")
        sys.stdout.flush()

    process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, bufsize=1)
    
    last_print = 0
    max_percent = 0.0
    try:
        while True:
            # Read until \r or \n to catch progress updates
            line = ""
            while True:
                char = process.stderr.read(1)
                if not char: break
                if char in ['\r', '\n']: break
                line += char
            
            if not char and not line: break
            
            line = line.strip()
            if not line: continue
            
            # Find percentage: look for "XX.X%" or "XX%"
            match = re.search(r'(\d+(?:\.\d+)?)%', line)
            if match:
                try:
                    curr_percent = float(match.group(1))
                    # Ensure progress only increases
                    max_percent = max(max_percent, curr_percent)
                    percent_str = f"{max_percent:.1f}" # Always show one decimal place
                except ValueError:
                    percent_str = match.group(1)

                curr_time = time.time()
                if curr_time - last_print >= interval:
                    # Extra info: speed or size
                    extra = ""
                    speed_match = re.search(r'(\d+\.?\d*\s*[KMG]B/s)', line)
                    if speed_match:
                        extra = f" ({speed_match.group(1)})"
                    
                    status_text = f"{prefix}: {percent_str}%{extra}"
                    if manager and worker_id:
                        manager.update(worker_id, status_text)
                    else:
                        sys.stdout.write(f"\r\033[K{status_text}")
                        sys.stdout.flush()
                    last_print = curr_time
    finally:
        process.wait()
    
    # Clear the progress line if we're not using a manager
    if not manager:
        sys.stdout.write(f"\r\033[K")
        sys.stdout.flush()
        
    return process.returncode == 0

def extract_resource(source_zst, target_dir, silent=False):
    """Integrated zst + tar extraction."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if not silent:
        print(_("python_extracting_to", "Extracting {file} to {dir}...", file=source_zst.name, dir=target_dir))
    
    if platform.system() != "Windows":
        # On Mac/Linux, try to use system tools
        try:
            # Try tar with built-in zstd support (modern tar)
            res = subprocess.run(["tar", "--zstd", "-xf", str(source_zst), "-C", str(target_dir)], capture_output=True)
            if res.returncode == 0: return True
            
            # Fallback: unzstd pipe to tar
            cmd = f"unzstd -c {source_zst} | tar -xf - -C {target_dir}"
            res = subprocess.run(cmd, shell=True, capture_output=True)
            if res.returncode == 0: return True
        except Exception as e:
            print(_("python_extraction_failed", "Extraction failed: {error}", error=e))
    else:
        # Windows logic (TBD: bundle zstd or use powershell)
        print(_("python_windows_extraction_warning", "Windows extraction requires zstd installed in PATH."))
        
    return False

def resolve_python_version(version_str=None):
    tag = get_system_tag()
    # Check local installations first
    if not INSTALL_DIR.exists():
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    
    if not version_str:
        # Pick latest installed
        installed = [d.name for d in INSTALL_DIR.iterdir() if d.is_dir()]
        matching = [v for v in installed if tag in v]
        if matching: return sorted(matching, reverse=True)[0]
        return f"python3.10.19" # Hard fallback

    if (INSTALL_DIR / version_str).exists(): return version_str
    if (INSTALL_DIR / f"{version_str}-{tag}").exists(): return f"{version_str}-{tag}"
    if (INSTALL_DIR / f"python{version_str}-{tag}").exists(): return f"python{version_str}-{tag}"
    
    return version_str

def get_python_exec(version=None):
    full_version = resolve_python_version(version)
    
    # Path for extracted binaries
    path_unix = INSTALL_DIR / full_version / "install" / "bin" / "python3"
    path_win = INSTALL_DIR / full_version / "install" / "python.exe"
    
    is_unix = sys.platform != "win32"
    exec_path = str(path_unix) if is_unix else str(path_win)
    
    if os.path.exists(exec_path):
        return exec_path
        
    return "python3"
