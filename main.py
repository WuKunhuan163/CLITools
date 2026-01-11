#!/usr/bin/env python3
import os
import sys
import subprocess
import json
import stat
import shutil
from pathlib import Path

def install_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    # Install tools into a 'tool' subdirectory
    tool_parent_dir = project_root / "tool"
    tool_parent_dir.mkdir(exist_ok=True)
    tool_dir = tool_parent_dir / tool_name
    bin_dir = project_root / "bin"
    
    # 0. Validate against global tool.json
    registry_path = project_root / "tool.json"
    if registry_path.exists():
        with open(registry_path, 'r') as f:
            registry = json.load(f)
            if tool_name not in registry.get("tools", {}):
                print(f"Error: Tool '{tool_name}' is not in the global registry.")
                return

    # 1. If tool directory doesn't exist, try to download from GitHub 'tool' branch
    if not tool_dir.exists():
        print(f"Tool {tool_name} not found locally. Attempting to fetch from 'tool' branch...")
        try:
            # Try to checkout from origin/tool - note the path is tool/<name> in the branch
            result = subprocess.run(["git", "checkout", "origin/tool", "--", f"tool/{tool_name}"], capture_output=True, cwd=str(project_root))
            if result.returncode != 0:
                # If remote fails, try local tool branch
                subprocess.run(["git", "checkout", "tool", "--", f"tool/{tool_name}"], check=True, capture_output=True, cwd=str(project_root))
            print(f"Successfully retrieved {tool_name} from 'tool' branch.")
        except subprocess.CalledProcessError as e:
            # Fallback for old branch structure or if tool is in root
            try:
                result = subprocess.run(["git", "checkout", "origin/tool", "--", tool_name], capture_output=True, cwd=str(project_root))
                if result.returncode == 0:
                    # Move from root to tool/
                    shutil.move(str(project_root / tool_name), str(tool_dir))
                    print(f"Successfully retrieved {tool_name} from 'tool' branch (root) and moved to tool/ folder.")
                else:
                    print(f"Error retrieving tool {tool_name}: {e}")
                    return
            except Exception:
                print(f"Error retrieving tool {tool_name}: {e}")
                return

    if not tool_dir.exists():
        print(f"Error: Tool directory {tool_dir} still not found after download attempt.")
        return

    # 2. Parse tool.json for dependencies
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        with open(tool_json_path, 'r') as f:
            tool_data = json.load(f)
            dependencies = tool_data.get("dependencies", [])
            for dep in dependencies:
                print(f"Installing dependency for {tool_name}: {dep}")
                install_tool(dep)

    # 2.1 Handle pip dependencies if requirements.txt exists
    requirements_path = tool_dir / "proj" / "requirements.txt"
    if not requirements_path.exists():
        requirements_path = tool_dir / "requirements.txt"
    
    if requirements_path.exists():
        print(f"Found requirements.txt for {tool_name}. Installing pip dependencies...")
        try:
            # Use the installed PYTHON tool to get the python executable
            python_tool_dir = project_root / "tool" / "PYTHON"
            if not python_tool_dir.exists():
                print("Warning: PYTHON tool not found. Skipping pip dependencies.")
            else:
                # Import get_python_exec from tool/PYTHON/proj/utils.py
                python_utils_path = python_tool_dir / "proj" / "utils.py"
                if python_utils_path.exists():
                    import importlib.util
                    spec = importlib.util.spec_from_file_location("python_utils_mod", str(python_utils_path))
                    python_utils_mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(python_utils_mod)
                    python_exec = python_utils_mod.get_python_exec()
                    # Run pip install using the standalone python
                    subprocess.run([python_exec, "-m", "pip", "install", "-r", str(requirements_path)], check=True)
                    print(f"Successfully installed pip dependencies for {tool_name}.")
        except Exception as e:
            print(f"Warning: Failed to install pip dependencies for {tool_name}: {e}")

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        print(f"Error: {main_py} not found in tool directory.")
        return

    # 3. Create bin directory
    bin_dir.mkdir(exist_ok=True)
    
    # 4. Create entry point in bin directory
    link_path = bin_dir / tool_name
    if link_path.exists() or link_path.is_symlink():
        os.remove(link_path)
    
    try:
        # Ensure main.py is executable
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)

        # Check if the tool depends on PYTHON. If so, create a wrapper script.
        use_wrapper = False
        if tool_json_path.exists():
            with open(tool_json_path, 'r') as f:
                tool_data = json.load(f)
                if "PYTHON" in tool_data.get("dependencies", []):
                    use_wrapper = True
        
        if use_wrapper:
            # Create a wrapper script that uses the standalone python
            wrapper_content = f'''#!/usr/bin/env python3
import sys
import os
import subprocess
from pathlib import Path

# Add the directory containing 'proj' to PYTHONPATH for the subprocess
project_root = Path({repr(str(project_root))})
python_tool_dir = project_root / "tool" / "PYTHON"
sys.path.append(str(python_tool_dir))

try:
    from proj.utils import get_python_exec
    python_exec = get_python_exec()
except ImportError:
    python_exec = "python3"

# Set up environment
env = os.environ.copy()
# Add the tool's directory to PYTHONPATH so it can find its own 'proj'
tool_main = Path({repr(str(main_py))})
env["PYTHONPATH"] = f"{{tool_main.parent}}:{{env.get('PYTHONPATH', '')}}"

if __name__ == "__main__":
    result = subprocess.run([python_exec, str(tool_main)] + sys.argv[1:], env=env)
    sys.exit(result.returncode)
'''
            with open(link_path, 'w') as f:
                f.write(wrapper_content)
            os.chmod(link_path, st.st_mode | stat.S_IEXEC)
            print(f"Successfully installed {tool_name}: wrapper created at {link_path}")
        else:
            # Traditional symlink
            os.symlink(main_py, link_path)
            print(f"Successfully installed {tool_name}: symlink created at {link_path}")
        
        # 5. Handle PATH registration
        register_path(bin_dir)
    except OSError as e:
        print(f"Error creating symlink for {tool_name}: {e}")

def register_path(bin_dir):
    """Add bin_dir to shell profile if not already present."""
    home = Path.home()
    shell = os.environ.get("SHELL", "")
    profiles = []
    if "zsh" in shell:
        profiles.append(home / ".zshrc")
    elif "bash" in shell:
        profiles.append(home / ".bash_profile")
        profiles.append(home / ".bashrc")
    else:
        profiles.extend([home / ".zshrc", home / ".bash_profile", home / ".bashrc"])

    export_cmd = f'\nexport PATH="{bin_dir}:$PATH"\n'
    
    for profile in profiles:
        if profile.exists():
            with open(profile, 'r') as f:
                content = f.read()
            if str(bin_dir) not in content:
                with open(profile, 'a') as f:
                    f.write(export_cmd)
                print(f"Updated {profile} with PATH.")
            else:
                # Already exists
                pass
    
    # Update current session's os.environ
    if str(bin_dir) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{bin_dir}:" + os.environ["PATH"]

def generate_ai_rule():
    project_root = Path(__file__).parent.absolute()
    registry_path = project_root / "tool.json"
    
    if not registry_path.exists():
        print("Error: Global tool.json not found.")
        return

    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    tools = registry.get("tools", {})
    installed_tools = []
    available_tools = []
    
    for name, info in tools.items():
        if (project_root / "tool" / name).exists():
            installed_tools.append((name, info))
        else:
            available_tools.append((name, info))
            
    print("--- AI AGENT TOOL RULES ---")
    print("CRITICAL: When developing or performing tasks, always prefer using the following integrated tools instead of writing custom implementations.")
    print("This ensures consistency, leverages optimized logic, and improves development efficiency.")
    print("\n[INSTALLED TOOLS - Use these directly]")
    for name, info in installed_tools:
        print(f"- {name}: {info.get('description')} (Purpose: {info.get('purpose')})")
        
    print("\n[AVAILABLE TOOLS - Use 'TOOL install <NAME>' before use]")
    for name, info in available_tools:
        print(f"- {name}: {info.get('description')} (Purpose: {info.get('purpose')})")
        
    print("\nNOTE: To use a tool, ensure its executable name (e.g., 'USERINPUT') is called directly in the terminal.")
    print("--------------------------")

def test_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / "tool" / tool_name
    
    if not tool_dir.exists():
        print(f"Error: Tool directory {tool_dir} not found.")
        return

    # Import TestRunner from proj.test_runner
    sys.path.append(str(project_root))
    try:
        from proj.test_runner import TestRunner
    except ImportError:
        print("Error: Could not import TestRunner from proj.test_runner.")
        return

    runner = TestRunner(tool_name, project_root)
    
    args = sys.argv[3:]
    list_only = "--list" in args
    
    if list_only:
        runner.list_tests()
        return

    start_id = None
    end_id = None
    max_concurrent = 3

    if "--range" in args:
        idx = args.index("--range")
        if idx + 2 < len(args):
            try:
                start_id = int(args[idx+1])
                end_id = int(args[idx+2])
            except ValueError:
                print("Error: --range requires two integer arguments.")
                return
    
    if "--max" in args:
        idx = args.index("--max")
        if idx + 1 < len(args):
            try:
                max_concurrent = int(args[idx+1])
            except ValueError:
                print("Error: --max requires an integer argument.")
                return

    runner.run_tests(start_id, end_id, max_concurrent)

def main():
    if len(sys.argv) < 2:
        print("Usage: TOOL <command> [args]")
        print("Commands: install, test, rule")
        sys.exit(1)

    command = sys.argv[1]
    if command == "install" and len(sys.argv) >= 3:
        install_tool(sys.argv[2])
    elif command == "test" and len(sys.argv) >= 3:
        test_tool(sys.argv[2])
    elif command == "rule":
        generate_ai_rule()
    else:
        print(f"Unknown command or missing arguments: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
