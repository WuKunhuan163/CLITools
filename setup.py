#!/usr/bin/env python3
import os
import sys
import stat
from pathlib import Path

def setup():
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
        print(f"Created {init_py}")

    tool_bin = bin_dir / "TOOL"
    
    # 1. Ensure main.py is executable
    if main_py.exists():
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
    else:
        print(f"Error: {main_py} not found. Please create main.py first.")
        sys.exit(1)

    # 2. Create bin/TOOL symlink
    try:
        # Delete existing symlink or file to handle corruption or updates
        if tool_bin.exists() or tool_bin.is_symlink():
            if tool_bin.is_dir():
                shutil.rmtree(tool_bin)
            else:
                os.remove(tool_bin)
        
        os.symlink(main_py, tool_bin)
        print(f"Successfully created/updated symlink: {tool_bin} -> {main_py}")
    except Exception as e:
        print(f"Error creating symlink: {e}")
        
    # 2.5. Install dependencies from tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        try:
            import json
            import subprocess
            with open(registry_path, 'r') as f:
                registry = json.load(f)
            
            # 2.5.1. Pip dependencies
            pip_deps = registry.get("dependencies", [])
            if pip_deps:
                print(f"Installing project pip dependencies: {', '.join(pip_deps)}...")
                # Use sys.executable to ensure we use the same python environment
                subprocess.run([sys.executable, "-m", "pip", "install"] + pip_deps, check=True)
                print("Pip dependencies installed successfully.")
            
            # 2.5.2. Tool dependencies (Core system dependencies)
            tool_deps = registry.get("tool_dependencies", [])
            if tool_deps:
                print(f"Checking core tool dependencies: {', '.join(tool_deps)}...")
                from logic.tool.setup.engine import ToolEngine
                for tool_name in tool_deps:
                    engine = ToolEngine(tool_name, project_root)
                    if not engine.is_installed():
                        print(f"Installing core tool dependency: {tool_name}...")
                        if engine.install():
                            print(f"Successfully installed core tool: {tool_name}")
                        else:
                            print(f"Error: Failed to install core tool: {tool_name}")
                    else:
                        print(f"Core tool {tool_name} is already operational.")

            # 2.5.3. Ensure Python standalone version for GUI if PYTHON tool is installed
            python_tool_dir = project_root / "tool" / "PYTHON"
            if python_tool_dir.exists():
                try:
                    sys.path.append(str(project_root))
                    from tool.PYTHON.logic.interface.main import get_python_exe_func
                    get_python_exe = get_python_exe_func()
                    
                    # We need 3.10.19 for GUI/Tkinter compatibility in this environment
                    print("Checking standalone Python 3.10.19 for GUI compatibility...")
                    py_exe = get_python_exe("3.10.19")
                    
                    # If it's the fallback 'python3', it means it's not installed
                    if not py_exe or py_exe == "python3":
                        print("Installing standalone Python 3.10.19...")
                        python_bin = project_root / "bin" / "PYTHON"
                        if not python_bin.exists():
                            python_bin = project_root / "tool" / "PYTHON" / "main.py"
                        
                        subprocess.run([sys.executable, str(python_bin), "--py-install", "3.10.19"], check=True)
                        py_exe = get_python_exe("3.10.19")
                    
                    if py_exe and py_exe != "python3":
                        print(f"Standalone Python 3.10.19 is ready at: {py_exe}")
                    else:
                        print("Warning: Failed to prepare standalone Python 3.10.19.")
                except Exception as e:
                    print(f"Warning during Python standalone check: {e}")

        except Exception as e:
            print(f"Warning: Failed to handle dependencies: {e}")

    # 3. Create TOOL alias in shell profiles for persistence (as a fallback/convenience)
    home = Path.home()
    profiles = [
        home / ".zshrc",
        home / ".bash_profile",
        home / ".bashrc"
    ]

    # Use the bin/TOOL as the target for the alias
    alias_cmd = f"alias TOOL='{tool_bin}'"
    
    for profile in profiles:
        try:
            if profile.exists():
                with open(profile, 'r') as f:
                    content = f.read()
                
                if f"alias TOOL=" not in content:
                    with open(profile, 'a') as f:
                        f.write(f"\n{alias_cmd}\n")
                    print(f"Successfully added TOOL alias to {profile}")
                else:
                    # Update existing alias
                    import re
                    pattern = r"alias TOOL=['\"].*?['\"]"
                    if str(tool_bin) in content:
                        pass
                    else:
                        new_content = re.sub(pattern, alias_cmd, content)
                        if new_content != content:
                            with open(profile, 'w') as f:
                                f.write(new_content)
                            print(f"Updated TOOL alias in {profile}")
                        else:
                            with open(profile, 'a') as f:
                                f.write(f"\n{alias_cmd}\n")
                            print(f"Added new TOOL alias to {profile}")
            
            # Also ensure bin_dir is in PATH
            if str(bin_dir) not in os.environ.get("PATH", ""):
                export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
                with open(profile, 'r') as f:
                    p_content = f.read()
                if str(bin_dir) not in p_content:
                    with open(profile, 'a') as f:
                        f.write(export_cmd)
                    print(f"Added {bin_dir} to PATH in {profile}")

        except Exception as e:
            print(f"Warning: Could not update {profile}: {e}")

if __name__ == "__main__":
    setup()
