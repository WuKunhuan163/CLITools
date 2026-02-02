#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import argparse
import platform
import json
from pathlib import Path

# Fix shadowing: Remove script directory from sys.path[0] if present
script_dir = Path(__file__).resolve().parent
if sys.path and sys.path[0] == str(script_dir):
    del sys.path[0]

# Add project root to sys.path to find root 'logic' and other 'tool' modules
project_root = script_dir.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from logic.turing.models.progress import ProgressTuringMachine
    from logic.turing.logic import TuringStage
    from logic.lang.utils import get_translation
    from logic.utils import get_logic_dir
except ImportError:
    class ProgressTuringMachine:
        def add_stage(self, stage): stage.action()
        def run(self, **kwargs): return True
    class TuringStage:
        def __init__(self, **kwargs): self.action = kwargs.get('action')
    def get_translation(d, k, default): return default
    def get_logic_dir(d): return d / "logic"

TOOL_INTERNAL = script_dir / "logic"

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
        
    from logic.utils import regularize_version_name
    version = regularize_version_name(args.py_version)

    def install_python():
        try:
            cmd = [str(python_bin), "--py-install", version]
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except:
            return False

    def test_gui():
        # Test window (3 seconds wait)
        try:
            # Run USERINPUT with a hint and a unique ID for precise targeting
            import uuid
            setup_id = f"setup_{uuid.uuid4().hex[:8]}"
            test_hint = "Setup OK!"
            test_cmd = ["python3", str(script_dir / "main.py"), "--timeout", "15", "--hint", test_hint, "--id", setup_id]
            env = os.environ.copy()
            # Ensure PYTHONPATH doesn't cause shadowing during test
            env["PYTHONPATH"] = f"{project_root}:{env.get('PYTHONPATH', '')}"
            
            # Start in background
            proc = subprocess.Popen(test_cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            time.sleep(2)
            
            # Use surgical stop - send SUBMIT remotely to close immediately
            # We use 'submit' with the unique ID to target ONLY our test instance
            stop_cmd = ["python3", str(script_dir / "main.py"), "submit", "--id", setup_id]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            # Wait for process to exit and capture output
            try:
                stdout, stderr = proc.communicate(timeout=10)
                all_out = stdout + stderr
                return test_hint in all_out and any(m in all_out for m in ["Successfully received", "成功收到"])
            except:
                proc.kill()
                return False
        except:
            return False

    tm = ProgressTuringMachine()
    tm.add_stage(TuringStage(
        name=f"Python {version}",
        action=install_python,
        active_status="Provisioning",
        success_status="Ready",
        fail_status="Failed to provision"
    ))
    
    tm.add_stage(TuringStage(
        name="GUI environment",
        action=test_gui,
        active_status="Verifying",
        success_status="Verified",
        fail_status="Verification failed"
    ))
    
    if tm.run(ephemeral=True):
        return 0
    return 1

if __name__ == "__main__":
    main()
