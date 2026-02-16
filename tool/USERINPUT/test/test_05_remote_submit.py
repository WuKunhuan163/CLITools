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
        
        # Start USERINPUT in background
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "60"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for window to appear and capture its PID from stdout
            gui_pid = None
            start_wait = time.time()
            while time.time() - start_wait < 20:
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

            # Send remote submit
            submit_cmd = ["python3", str(main_py), "submit", str(gui_pid)]
            subprocess.run(submit_cmd, env=env, capture_output=True)
            
            # Wait for exit
            stdout, stderr = proc.communicate(timeout=20)
            
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

