#!/usr/bin/env python3
import os
import sys
import stat
from pathlib import Path

def setup():
    project_root = Path(__file__).parent.absolute()
    main_py = project_root / "main.py"
    tool_link = project_root / "TOOL"
    
    # 1. Ensure main.py is executable
    if main_py.exists():
        st = os.stat(main_py)
        os.chmod(main_py, st.st_mode | stat.S_IEXEC)
    else:
        print(f"Error: {main_py} not found. Please create main.py first.")
        sys.exit(1)
        
    # 2. Create TOOL alias in shell profiles for persistence
    home = Path.home()
    profiles = [
        home / ".zshrc",
        home / ".bash_profile",
        home / ".bashrc"
    ]

    alias_cmd = f"alias TOOL='python3 {main_py}'"
    
    for profile in profiles:
        try:
            if profile.exists():
                with open(profile, 'r') as f:
                    content = f.read()
                
                # Check if alias already exists (any version of it)
                if f"alias TOOL=" not in content:
                    with open(profile, 'a') as f:
                        f.write(f"\n{alias_cmd}\n")
                    print(f"Successfully added TOOL alias to {profile}")
                else:
                    # Update existing alias if it's different
                    import re
                    pattern = r"alias TOOL=['\"].*?['\"]"
                    # If it matches exactly, do nothing
                    if f"'{main_py}'" in content or f"\"{main_py}\"" in content:
                        print(f"TOOL alias already correct in {profile}")
                    else:
                        new_content = re.sub(pattern, alias_cmd, content)
                        if new_content != content:
                            with open(profile, 'w') as f:
                                f.write(new_content)
                            print(f"Updated TOOL alias in {profile}")
                        else:
                            # Fallback if pattern didn't match perfectly but "alias TOOL=" exists
                            with open(profile, 'a') as f:
                                f.write(f"\n{alias_cmd}\n")
                            print(f"Added new TOOL alias to {profile} (existing one was different)")
            else:
                # Optional: create file and add alias if it's a known profile name?
                # For now, just skip if it doesn't exist
                pass
        except Exception as e:
            print(f"Warning: Could not update {profile}: {e}")

    # 3. Create TOOL symlink (legacy compatibility)
    if tool_link.exists() or tool_link.is_symlink():
        os.remove(tool_link)
    
    try:
        os.symlink(main_py, tool_link)
        print(f"Successfully created symlink: TOOL -> {main_py}")
    except OSError as e:
        print(f"Error creating symlink: {e}")

    # 4. Create global data directory
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    print(f"Ensured data directory exists: {data_dir}")

if __name__ == "__main__":
    setup()

