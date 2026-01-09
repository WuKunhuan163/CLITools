#!/Applications/AITerminalTools/PYTHON_PROJ/python3.10.19/install/bin/python3
import os
import sys
import json
import shutil
import subprocess
import stat
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: TOOL <command> [args]")
        print("Commands:")
        print("  install <tool_name>  - Install a tool")
        print("  test <tool_name>     - Test a tool")
        sys.exit(1)

    command = sys.argv[1]
    
    if command == "install":
        if len(sys.argv) < 3:
            print("Usage: TOOL install <tool_name>")
            sys.exit(1)
        install_tool(sys.argv[2])
    elif command == "test":
        if len(sys.argv) < 3:
            print("Usage: TOOL test <tool_name>")
            sys.exit(1)
        test_tool(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

def install_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / tool_name
    bin_dir = project_root / "bin"
    
    # 1. If tool directory doesn't exist, try to download from GitHub 'tool' branch
    if not tool_dir.exists():
        print(f"Tool {tool_name} not found locally. Attempting to fetch from 'tool' branch...")
        try:
            # Try to checkout from origin/tool
            result = subprocess.run(["git", "checkout", "origin/tool", "--", tool_name], capture_output=True, cwd=str(project_root))
            if result.returncode != 0:
                # If remote fails, try local tool branch
                subprocess.run(["git", "checkout", "tool", "--", tool_name], check=True, capture_output=True, cwd=str(project_root))
            print(f"Successfully retrieved {tool_name} from 'tool' branch.")
        except subprocess.CalledProcessError as e:
            print(f"Error retrieving tool {tool_name}: {e}")
            return

    if not tool_dir.exists():
        print(f"Error: Tool directory {tool_dir} still not found after download attempt.")
        return

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        # Maybe it's in the root of the tool folder but named differently? 
        # No, the new structure requires main.py
        print(f"Error: {main_py} not found in tool directory.")
        return

    # 2. Create bin directory
    bin_dir.mkdir(exist_ok=True)
    
    # 3. Create symlink in bin directory
    link_path = bin_dir / tool_name
    if link_path.exists() or link_path.is_symlink():
        os.remove(link_path)
    
    try:
        os.symlink(main_py, link_path)
        # Ensure main.py is executable
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
        print(f"Successfully installed {tool_name}: symlink created at {link_path}")
        print(f"Note: Please ensure {bin_dir} is in your PATH.")
    except OSError as e:
        print(f"Error creating symlink for {tool_name}: {e}")

def test_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / tool_name
    
    if not tool_dir.exists():
        print(f"Error: Tool directory {tool_dir} not found.")
        return

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        print(f"Error: {main_py} not found.")
        return

    print(f"Testing tool: {tool_name}")
    try:
        # Run tool with --help as a basic test
        subprocess.run([sys.executable, str(main_py), "--help"], check=True)
        print(f"Test for {tool_name} passed.")
    except subprocess.CalledProcessError as e:
        print(f"Test for {tool_name} failed: {e}")

if __name__ == "__main__":
    main()

