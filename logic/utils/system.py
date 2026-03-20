"""Platform detection, path resolution, Python execution, and system utilities."""
import os
import sys
import subprocess
import platform
from pathlib import Path


def get_system_tag():
    """Detect current system tag for Python downloads."""
    system = sys.platform
    machine = platform.machine().lower()
    if system == "darwin":
        return "macos-arm64" if "arm" in machine or "aarch64" in machine else "macos"
    if system == "linux":
        try:
            with open("/etc/os-release", "r") as f:
                if "alpine" in f.read().lower(): return "linux64-musl"
        except: pass
        return "linux64"
    if system == "win32":
        if "arm" in machine: return "windows-arm64"
        return "windows-amd64" if "64" in machine else "windows-x86"
    return "unknown"

def regularize_version_name(version, platform=None):
    """Standardize version name to 'X.Y.Z-platform' (no 'python' prefix)."""
    v = str(version)
    if v.startswith("python"):
        v = v[6:]
    if "-" in v:
        v = v.split("-")[0]
    plat = platform or get_system_tag()
    return f"{v}-{plat}"

def extract_resource(source_zst, target_dir, silent=False):
    """Integrated zst + tar extraction."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if not silent:
        print(f"Extracting {source_zst.name}...")
    
    if sys.platform != "win32":
        try:
            res = subprocess.run(["tar", "--zstd", "-xf", str(source_zst), "-C", str(target_dir)], capture_output=True)
            if res.returncode == 0: return True
            cmd = f"unzstd -c {source_zst} | tar -xf - -C {target_dir}"
            res = subprocess.run(cmd, shell=True, capture_output=True)
            if res.returncode == 0: return True
        except: pass
    return False

def print_missing_tool_error(tool_name, dep_name, script_dir, translation_func=None):
    """Unified error reporting for missing tool dependency."""
    _ = translation_func or (lambda k, d: d)
    
    from logic._.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")
    
    error_label = _("label_error", "Error")
    print(f"{BOLD}{RED}{error_label}{RESET}: " + _("err_tool_not_found", "Tool '{dep_name}' not found, required by '{tool_name}'.").format(dep_name=dep_name, tool_name=tool_name), flush=True)
    print(_("err_tool_install_hint", "Please run: TOOL install {dep_name}").format(dep_name=dep_name), flush=True)
    
    setup_path = script_dir / "setup.py"
    if setup_path.exists():
        print(_("err_tool_setup_hint", "Finally, run tool's setup: {tool_name} setup").format(tool_name=tool_name), flush=True)
    else:
        print(_("err_tool_setup_hint", "Finally, run tool's setup: TOOL install {tool_name}").format(tool_name=tool_name), flush=True)

def print_python_not_found_error(tool_name, version, script_dir, translation_func=None):
    """Unified error reporting for missing Python version."""
    _ = translation_func or (lambda k, d: d)
    
    from logic._.config import get_color
    BOLD = get_color("BOLD", "\033[1m")
    RED = get_color("RED", "\033[31m")
    RESET = get_color("RESET", "\033[0m")
    
    error_label = _("label_error", "Error")
    msg = _("err_python_not_found", "Python tool '{version}' not found, cannot launch {tool_name} GUI.").format(version=version, tool_name=tool_name)
    sys.stdout.write(f"{BOLD}{RED}{error_label}{RESET}: {msg}\n")
    
    sys.stdout.write(_("err_python_not_found_hint_2", "Please run: TOOL install PYTHON") + "\n")
    sys.stdout.write(_("err_python_not_found_hint_3", "Then run: PYTHON --py-install {version}").format(version=version) + "\n")
    
    download_hint = _("err_python_download_hint", "To download a missing version: PYTHON --py-update --version {version}").format(version=version)
    sys.stdout.write(download_hint + "\n")
    
    setup_path = script_dir / "setup.py"
    if setup_path.exists():
        sys.stdout.write(_("err_python_not_found_hint_4", "Finally, run tool's setup: {tool_name} setup").format(tool_name=tool_name) + "\n")
    else:
        sys.stdout.write(_("err_python_not_found_hint_4", "Finally, run tool's setup: TOOL install {tool_name}").format(tool_name=tool_name) + "\n")
    sys.stdout.flush()

def get_python_tool_exec():
    """Find the PYTHON tool's executable path."""
    project_root = Path(__file__).resolve().parent.parent.parent
    python_tool_dir = project_root / "tool" / "PYTHON"
    if not python_tool_dir.exists():
        return None
    
    try:
        if str(project_root) not in sys.path:
            sys.path.append(str(project_root))
        from tool.PYTHON.logic.utils import get_python_exec as gpe
        res = gpe()
        if res == "python3":
            return None
        return res
    except:
        return None

get_python_exec = get_python_tool_exec

def check_and_reexecute_with_python(tool_name, version=None):
    """
    Ensure the current script is running with the correct PYTHON tool executable.
    If not, re-execute. If PYTHON is missing, print helpful error and exit.
    """
    if os.environ.get("TOOL_MANAGED_PYTHON_ACTIVE") == "1":
        return

    if version is None:
        from logic._.config import get_setting
        version = get_setting("default_python_version", "3.11.14")
        
    project_root = Path(__file__).resolve().parent.parent.parent
    py_exec = get_python_tool_exec()
    
    if py_exec:
        target_py = str(Path(py_exec).resolve())
        current_py = str(Path(sys.executable).resolve())
        
        if current_py != target_py:
            env = os.environ.copy()
            env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
            env["TOOL_MANAGED_PYTHON_ACTIVE"] = "1"
            
            script_path = sys.argv[0]
            extra_args = [a for a in sys.argv[1:] if a not in ["--no-warning", "--tool-quiet"]]
            
            os.execve(py_exec, [py_exec, script_path] + extra_args, env)
    
    if not py_exec:
        print_python_not_found_error(tool_name, version, project_root / "tool" / tool_name)
        sys.exit(1)

def get_logic_dir(base_dir):
    """Returns the logic directory path for a given base directory."""
    return Path(base_dir) / "logic"

from logic.utils.resolve import find_project_root, get_tool_module_path  # canonical implementations

def get_module_relative_path(module_name: str) -> str:
    """
    Translates a module name (e.g. 'logic.tool.base') to its relative path 
    from the project root (e.g. 'logic/tool/base.py' or 'logic/tool/base/').
    """
    path_parts = module_name.split('.')
    return os.path.join(*path_parts)

def register_path(bin_dir):
    """Add bin directory to PATH in shell profiles."""
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    profiles = []
    if "zsh" in shell: profiles.append(home / ".zshrc")
    elif "bash" in shell:
        profiles.append(home / ".bash_profile")
        profiles.append(home / ".bashrc")
    else: profiles.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
    for profile in profiles:
        if profile.exists():
            try:
                with open(profile, 'r') as f: content = f.read()
                if str(bin_dir) not in content:
                    with open(profile, 'a') as f: f.write(export_cmd)
            except: pass

    if str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:" + os.environ["PATH"]

def get_tool_bin_path(project_root, tool_name):
    """Resolve the path to a tool's executable in bin/, supporting both new
    (bin/<tool>/<tool>) and legacy (bin/<tool>) structures."""
    project_root = Path(project_root)
    shortcut_name = tool_name.split(".")[-1] if "." in tool_name else tool_name
    new_path = project_root / "bin" / shortcut_name / shortcut_name
    if new_path.exists():
        return new_path
    legacy = project_root / "bin" / shortcut_name
    if legacy.exists() and legacy.is_file():
        return legacy
    return new_path

def get_cpu_percent(interval=0.1):
    """Returns the current system-wide CPU utilization as a percentage."""
    try:
        import psutil
        return psutil.cpu_percent(interval=interval)
    except ImportError:
        return 0.0
    except Exception:
        return 0.0

def detect_ide() -> str:
    """Detect the current IDE/editor environment.

    Returns one of: 'cursor', 'vscode', 'terminal', 'unknown'.
    Detection is based on environment variables and filesystem markers.
    """
    if os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_TRACE_ID"):
        return "cursor"

    for key in os.environ:
        if key.startswith("CURSOR_"):
            return "cursor"

    term_program = os.environ.get("TERM_PROGRAM", "").lower()
    if term_program == "vscode":
        vscode_ipc = os.environ.get("VSCODE_IPC_HOOK", "")
        if "cursor" in vscode_ipc.lower():
            return "cursor"
        return "vscode"

    if os.environ.get("VSCODE_PID") or os.environ.get("VSCODE_IPC_HOOK_CLI"):
        return "vscode"

    return "terminal"


def is_cursor_ide() -> bool:
    """Check if running inside Cursor IDE."""
    return detect_ide() == "cursor"


def is_vscode() -> bool:
    """Check if running inside VS Code (not Cursor)."""
    return detect_ide() == "vscode"


def get_variable_from_file(file_path, var_name, default=None):
    """Extract a top-level variable value from a Python file using AST."""
    import ast
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read())
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == var_name:
                        return ast.literal_eval(node.value)
    except Exception:
        pass
    return default
