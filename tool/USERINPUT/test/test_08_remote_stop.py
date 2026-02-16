import unittest
import subprocess
import time
import os
from pathlib import Path

class TestUserInputRemoteStop(unittest.TestCase):
    def test_remote_stop(self):
        """Test remote stop command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "30"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for window to appear and capture its PID from stdout
            gui_pid = None
            start_wait = time.time()
            while time.time() - start_wait < 15:
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

            # Send remote stop
            stop_cmd = ["python3", str(main_py), "stop", str(gui_pid)]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            # Wait for exit
            stdout, stderr = proc.communicate(timeout=15)
            
            all_out = stdout + stderr
            stop_indicators = ["Terminated", "已终止"]
            self.assertTrue(any(ind in all_out for ind in stop_indicators))
            self.assertEqual(proc.returncode, 0)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

