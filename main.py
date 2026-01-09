#!/usr/bin/env python3
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
        print("  rule                 - Generate AI Agent rules")
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
    elif command == "rule":
        generate_ai_rule()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

def install_tool(tool_name):
    project_root = Path(__file__).parent.absolute()
    tool_dir = project_root / tool_name
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

    # 2. Parse tool.json for dependencies
    tool_json_path = tool_dir / "tool.json"
    if tool_json_path.exists():
        with open(tool_json_path, 'r') as f:
            tool_data = json.load(f)
            dependencies = tool_data.get("dependencies", [])
            for dep in dependencies:
                print(f"Installing dependency for {tool_name}: {dep}")
                install_tool(dep)

    main_py = tool_dir / "main.py"
    if not main_py.exists():
        print(f"Error: {main_py} not found in tool directory.")
        return

    # 3. Create bin directory
    bin_dir.mkdir(exist_ok=True)
    
    # 4. Create symlink in bin directory
    link_path = bin_dir / tool_name
    if link_path.exists() or link_path.is_symlink():
        os.remove(link_path)
    
    try:
        os.symlink(main_py, link_path)
        # Ensure main.py is executable
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
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
        if (project_root / name).exists():
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

