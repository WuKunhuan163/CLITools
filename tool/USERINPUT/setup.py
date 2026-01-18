#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import argparse
import platform
from pathlib import Path

# Add project root to sys.path
script_dir = Path(__file__).resolve().parent
project_root = script_dir.parent.parent
sys.path.append(str(project_root))

try:
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
except ImportError:
    def get_translation(d, k, default): return default
    def get_logic_dir(d): return d / "logic"

TOOL_INTERNAL = get_logic_dir(script_dir)

def _(key, default):
    return get_translation(str(TOOL_INTERNAL), key, default)

def main():
    # Load config to get default python version
    config_path = TOOL_INTERNAL / "config.json"
    default_version = "python3.11.14"
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                default_version = json.load(f).get("python_version", default_version)
        except Exception: pass

    parser = argparse.ArgumentParser(description="USERINPUT Setup Tool")
    parser.add_argument("--py-version", default=default_version, help="Python version to install")
    args = parser.parse_args()

    python_bin = project_root / "bin" / "PYTHON"
    
    if not python_bin.exists():
        print("\033[1;31mError\033[0m: PYTHON tool binary not found.")
        sys.exit(1)
        
    from logic.utils import regularize_version_name, get_system_tag
    version = regularize_version_name(args.py_version)

    try:
        cmd = [str(python_bin), "--py-install", version]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        # If it failed, show the error
        try:
            sys.path.append(str(script_dir))
            from logic.utils import print_python_not_found_error
            print_python_not_found_error("USERINPUT", version, script_dir, _)
        except Exception:
            print(f"\033[1;31mError\033[0m: Failed to install {version}.")
        sys.exit(1)

    # Test window (2 seconds)
    print("Launching test window (2s)...")
    try:
        # Run USERINPUT with a hint and short timeout
        test_cmd = ["python3", str(script_dir / "main.py"), "--timeout", "2", "--hint", "Setup OK!"]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{project_root}:{script_dir}:{env.get('PYTHONPATH', '')}"
        
        proc = subprocess.run(test_cmd, env=env, timeout=5, capture_output=True, text=True)
        if proc.returncode == 0:
            print("\033[1;32mSuccess\033[0m: USERINPUT GUI is working.")
        else:
            print(f"Test window result: {proc.stdout.strip()}")
    except subprocess.TimeoutExpired:
        print("\033[1;32mSuccess\033[0m: USERINPUT GUI test timed out (as expected).")
    except Exception as e:
        print(f"\033[1;31mError\033[0m: GUI test failed: {e}")

if __name__ == "__main__":
    main()
