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
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from logic_internal.lang.utils import get_translation
    from logic_internal.utils import get_logic_dir
except ImportError:
    def get_translation(d, k, default): return default
    def get_logic_dir(d): return d / "logic"

TOOL_INTERNAL = script_dir / "logic_internal"

def _(key, default):
    return get_translation(str(TOOL_INTERNAL), key, default)

def main():
    # Load config to get default python version
    config_path = TOOL_INTERNAL / "config.json"
    default_version = "3.11.14"
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
        
    from logic_internal.utils import regularize_version_name, get_system_tag
    version = regularize_version_name(args.py_version)

    try:
        cmd = [str(python_bin), "--py-install", version]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        # If it failed, show the error
        try:
            sys.path.append(str(script_dir))
            from logic_internal.utils import print_python_not_found_error
            print_python_not_found_error("USERINPUT", version, script_dir, _)
        except Exception:
            print(f"\033[1;31mError\033[0m: Failed to install {version}.")
        sys.exit(1)

    # Test window (2 seconds)
    print("Launching test window...")
    try:
        # Run USERINPUT with a hint
        # We use a longer timeout but kill it surgically
        test_cmd = ["python3", str(script_dir / "main.py"), "--timeout", "10", "--hint", "Setup OK!"]
        env = os.environ.copy()
        env["PYTHONPATH"] = f"{project_root}:{script_dir}:{env.get('PYTHONPATH', '')}"
        
        # Start in background
        proc = subprocess.Popen(test_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(f"Test window started (PID: {proc.pid}). Waiting 2s...")
        import time
        time.sleep(2)
        
        # Use surgical stop
        print(f"Closing test window surgically (PID: {proc.pid})...")
        stop_cmd = [str(project_root / "bin" / "USERINPUT"), "stop", str(proc.pid)]
        subprocess.run(stop_cmd, capture_output=True)
        
        # Wait for process to exit
        try:
            proc.wait(timeout=5)
            print("\033[1;32mSuccess\033[0m: USERINPUT GUI setup test completed.")
        except subprocess.TimeoutExpired:
            proc.kill()
            print("\033[1;33mWarning\033[0m: USERINPUT GUI setup test forced to kill.")
            
    except Exception as e:
        print(f"\033[1;31mError\033[0m: GUI setup test failed: {e}")

if __name__ == "__main__":
    main()
