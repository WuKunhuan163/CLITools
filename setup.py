#!/usr/bin/env python3
import os
import sys
import stat
import json
import subprocess
from pathlib import Path
from logic.turing.models.progress import ProgressTuringMachine
from logic.turing.logic import TuringStage

# Colors
BOLD = "\033[1m"
GREEN = "\033[32m"
BLUE = "\033[34m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

def check_structure_action(stage=None):
    project_root = Path(__file__).parent.absolute()
    main_py = project_root / "main.py"
    bin_dir = project_root / "bin"
    tool_dir = project_root / "tool"
    
    bin_dir.mkdir(exist_ok=True)
    tool_dir.mkdir(exist_ok=True)
    
    # Ensure tool/__init__.py exists
    init_py = tool_dir / "__init__.py"
    if not init_py.exists():
        init_py.touch()

    # Ensure main.py is executable
    if main_py.exists():
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
    else:
        if stage: stage.error_brief = "main.py not found"
        return False

    # Create bin/TOOL symlink
    tool_bin = bin_dir / "TOOL"
    try:
        if tool_bin.exists() or tool_bin.is_symlink():
            if tool_bin.is_dir():
                import shutil
                shutil.rmtree(tool_bin)
            else:
                os.remove(tool_bin)
        os.symlink(main_py, tool_bin)
        return True
    except Exception as e:
        if stage: stage.error_brief = str(e)
        return False

def install_deps_action(stage=None):
    project_root = Path(__file__).parent.absolute()
    registry_path = project_root / "tool.json"
    if not registry_path.exists(): return True
    
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        pip_deps = registry.get("dependencies", [])
        if pip_deps:
            res = subprocess.run([sys.executable, "-m", "pip", "install"] + pip_deps, capture_output=True, text=True)
            if res.returncode != 0:
                if stage: stage.error_brief = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "pip install failed"
                return False
        return True
    except Exception as e:
        if stage: stage.error_brief = str(e)
        return False

def setup_keyboard_access_action(stage=None):
    """On macOS, verify accessibility permission for global keyboard monitoring."""
    import platform
    if platform.system() != "Darwin":
        return True
    try:
        from logic.accessibility.keyboard.monitor import check_accessibility_trusted
        if check_accessibility_trusted():
            return True
        from logic.accessibility.keyboard.monitor import request_accessibility_permission
        request_accessibility_permission()
        return True
    except Exception:
        return True


def install_core_tools_action(stage=None):
    project_root = Path(__file__).parent.absolute()
    registry_path = project_root / "tool.json"
    if not registry_path.exists(): return True
    
    try:
        with open(registry_path, 'r') as f:
            registry = json.load(f)
        
        tool_deps = registry.get("tool_dependencies", [])
        if tool_deps:
            from logic.tool.setup.engine import ToolEngine
            for tool_name in tool_deps:
                engine = ToolEngine(tool_name, project_root)
                if not engine.is_installed():
                    if not engine.install():
                        if stage: stage.error_brief = f"Failed to install {tool_name}"
                        return False
        return True
    except Exception as e:
        if stage: stage.error_brief = str(e)
        return False

def setup_gui_python_action(stage=None):
    project_root = Path(__file__).parent.absolute()
    python_tool_dir = project_root / "tool" / "PYTHON"
    if not python_tool_dir.exists(): return True
    
    try:
        sys.path.append(str(project_root))
        from tool.PYTHON.logic.interface.main import get_python_exe_func
        get_python_exe = get_python_exe_func()
        
        py_exe = get_python_exe("3.10.19")
        if not py_exe or py_exe == "python3":
            # Attempt installation
            python_bin = project_root / "bin" / "PYTHON" / "PYTHON"
            if not python_bin.exists():
                python_bin = project_root / "bin" / "PYTHON"
            if not python_bin.exists():
                python_bin = project_root / "tool" / "PYTHON" / "main.py"
            
            res = subprocess.run([sys.executable, str(python_bin), "--py-install", "3.10.19"], capture_output=True, text=True)
            if res.returncode != 0:
                # If install fails because of missing remote versions, try update once
                if "No versions found on remote" in res.stdout or "No versions found on remote" in res.stderr:
                    subprocess.run([sys.executable, str(python_bin), "--py-update", "--version", "3.10.19", "--limit", "1"], capture_output=True)
                    # Retry install
                    res = subprocess.run([sys.executable, str(python_bin), "--py-install", "3.10.19"], capture_output=True, text=True)
                
                if res.returncode != 0:
                    if stage: stage.error_brief = "Failed to install Python 3.10.19"
                    return False
        return True
    except Exception as e:
        if stage: stage.error_brief = str(e)
        return False

def shell_integration_action(stage=None):
    project_root = Path(__file__).parent.absolute()
    bin_dir = project_root / "bin"
    tool_bin = bin_dir / "TOOL"
    
    home = Path.home()
    profiles = [home / ".zshrc", home / ".bash_profile", home / ".bashrc"]
    alias_cmd = f"alias TOOL='{tool_bin}'"
    
    for profile in profiles:
        try:
            if profile.exists():
                with open(profile, 'r') as f: content = f.read()
                
                if f"alias TOOL=" not in content:
                    with open(profile, 'a') as f: f.write(f"\n{alias_cmd}\n")
                else:
                    import re
                    pattern = r"alias TOOL=['\"].*?['\"]"
                    if str(tool_bin) not in content:
                        new_content = re.sub(pattern, alias_cmd, content)
                        with open(profile, 'w') as f: f.write(new_content)
            
                if str(bin_dir) not in os.environ.get("PATH", ""):
                    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
                    with open(profile, 'r') as f: p_content = f.read()
                    if str(bin_dir) not in p_content:
                        with open(profile, 'a') as f: f.write(export_cmd)
        except Exception as e:
            if stage: stage.error_brief = str(e)
            return False
    return True

def setup():
    project_root = Path(__file__).parent.absolute()
    pm = ProgressTuringMachine(project_root=project_root)
    
    pm.add_stage(TuringStage(
        name="structure",
        action=check_structure_action,
        active_status="Checking",
        success_status="Successfully validated",
        fail_status="Failed to validate",
        success_color="BOLD",
        bold_part="Checking structure"
    ))
    
    pm.add_stage(TuringStage(
        name="dependencies",
        action=install_deps_action,
        active_status="Installing",
        success_status="Successfully installed",
        fail_status="Failed to install",
        success_color="BOLD",
        bold_part="Installing dependencies"
    ))

    pm.add_stage(TuringStage(
        name="keyboard access",
        action=setup_keyboard_access_action,
        active_status="Checking",
        success_status="Successfully verified",
        fail_status="Failed to verify",
        success_color="BOLD",
        bold_part="Checking keyboard access"
    ))

    pm.add_stage(TuringStage(
        name="core tools",
        action=install_core_tools_action,
        active_status="Setting up",
        success_status="Successfully set up",
        fail_status="Failed to set up",
        success_color="BOLD",
        bold_part="Setting up core tools"
    ))

    pm.add_stage(TuringStage(
        name="standalone python",
        action=setup_gui_python_action,
        active_status="Ensuring",
        success_status="Successfully set up",
        fail_status="Failed to set up",
        success_color="BOLD",
        bold_part="Ensuring standalone python"
    ))

    pm.add_stage(TuringStage(
        name="shell integration",
        action=shell_integration_action,
        active_status="Configuring",
        success_status="Successfully configured",
        fail_status="Failed to configure",
        success_color="BOLD",
        bold_part="Configuring shell integration"
    ))

    final_msg = f"setup AITerminalTools"
    if pm.run(ephemeral=True, final_msg=""):
        from logic.utils import print_success_status
        print_success_status(final_msg)

if __name__ == "__main__":
    setup()
