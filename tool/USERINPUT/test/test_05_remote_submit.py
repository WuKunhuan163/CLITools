import unittest
import subprocess
import time
import os
import json
from pathlib import Path

class TestUserInputRemoteSubmit(unittest.TestCase):
    def test_remote_submit(self):
        """Test remote submit command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        # Start USERINPUT in background
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        test_id = f"test_submit_{int(time.time())}_{os.getpid()}"
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "30", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register
            time.sleep(5)
            
            # Debug: check instances
            instance_dir = project_root / "data" / "run" / "instances"
            print(f"DEBUG: Checking instance dir: {instance_dir}")
            if instance_dir.exists():
                for f in instance_dir.glob("gui_*.json"):
                    with open(f, "r") as info_file:
                        print(f"DEBUG: Found instance file: {f.name} -> {info_file.read()}")
            else:
                print("DEBUG: Instance dir does not exist")

            # Send remote submit
            submit_cmd = ["python3", str(main_py), "submit", "--id", test_id]
            print(f"DEBUG: Running submit command: {' '.join(submit_cmd)}")
            res = subprocess.run(submit_cmd, env=env, capture_output=True, text=True)
            print(f"DEBUG: Submit stdout: {res.stdout}")
            print(f"DEBUG: Submit stderr: {res.stderr}")
            
            # Wait for exit
            stdout, stderr = proc.communicate(timeout=10)
            
            # Check for success indicators
            all_out = stdout + stderr
            success_indicators = ["Successfully received", "成功收到"]
            self.assertTrue(any(ind in all_out for ind in success_indicators))
            self.assertEqual(proc.returncode, 0)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

