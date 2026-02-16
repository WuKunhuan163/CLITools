import unittest
import subprocess
import time
import os
import json
from pathlib import Path

EXPECTED_CPU_LIMIT = 40.0

class TestUserInputRemoteSubmit(unittest.TestCase):
    def test_remote_submit(self):
        """Test remote submit command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        test_id = f"test_05_{int(time.time())}"
        
        # Start USERINPUT in background with unique ID
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        import sys
        python_exec = sys.executable
        
        proc = subprocess.Popen([python_exec, str(main_py), "--timeout", "60", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for window to appear and capture its PID from stdout
            gui_pid = None
            start_wait = time.time()
            while time.time() - start_wait < 30: # Increased timeout
                line = proc.stdout.readline()
                if not line: break
                if "(PID: " in line:
                    import re
                    match = re.search(r"\(PID: (\d+)\)", line)
                    if match:
                        gui_pid = int(match.group(1))
                        break
            
            if not gui_pid:
                self.fail("Could not capture GUI PID from stdout")

            # Wait for GUI to register in instances directory
            instance_found = False
            start_reg_wait = time.time()
            while time.time() - start_reg_wait < 15:
                instance_dir = project_root / "data" / "run" / "instances"
                if instance_dir.exists():
                    for f in instance_dir.glob("gui_*.json"):
                        try:
                            with open(f, 'r') as info_file:
                                info = json.load(info_file)
                                if info.get("custom_id") == test_id:
                                    instance_found = True
                                    break
                        except: pass
                if instance_found: break
                time.sleep(1)
            
            if not instance_found:
                self.fail(f"GUI instance with ID {test_id} not found in registry")

            # Send remote submit using ID
            submit_cmd = [python_exec, str(main_py), "submit", "--id", test_id]
            sub_res = subprocess.run(submit_cmd, env=env, capture_output=True, text=True)
            if sub_res.returncode != 0:
                self.fail(f"submit command failed: {sub_res.stderr}")
            
            # Wait for exit
            stdout, stderr = proc.communicate(timeout=40)
            
            # Check for success indicators
            all_out = stdout + stderr
            success_indicators = ["Successfully received", "成功收到"]
            self.assertTrue(any(ind in all_out for ind in success_indicators))
            self.assertEqual(proc.returncode, 0)
            
        finally:
            if proc.poll() is None:
                try:
                    import psutil
                    parent = psutil.Process(proc.pid)
                    for child in parent.children(recursive=True):
                        try: child.kill()
                        except: pass
                    proc.kill()
                except:
                    proc.kill()

if __name__ == '__main__':
    unittest.main()

