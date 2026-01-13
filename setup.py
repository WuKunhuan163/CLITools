#!/usr/bin/env python3
import os
import sys
import stat
from pathlib import Path

def setup():
    project_root = Path(__file__).parent.absolute()
    main_py = project_root / "main.py"
    bin_dir = project_root / "bin"
    bin_dir.mkdir(exist_ok=True)
    tool_bin = bin_dir / "TOOL"
    
    # 1. Ensure main.py is executable
    if main_py.exists():
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
    else:
        print(f"Error: {main_py} not found. Please create main.py first.")
        sys.exit(1)

    # 2. Create bin/TOOL wrapper script
    # This wrapper script calls main.py with all arguments
    wrapper_content = f"""#!/bin/bash
exec python3 "{main_py}" "$@"
"""
    try:
        with open(tool_bin, 'w') as f:
            f.write(wrapper_content)
        st = os.stat(tool_bin)
        os.chmod(tool_bin, st.st_mode | stat.S_IEXEC)
        print(f"Successfully created wrapper script: {tool_bin} -> {main_py}")
    except Exception as e:
        print(f"Error creating wrapper script: {e}")
        
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
