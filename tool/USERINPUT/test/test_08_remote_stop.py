import unittest
import subprocess
import time
import os
import json
from pathlib import Path

class TestUserInputRemoteStop(unittest.TestCase):
    def test_remote_stop(self):
        """Test remote stop command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # Use -u for unbuffered output to ensure we capture PID from stdout immediately
        proc = subprocess.Popen(["python3", "-u", str(main_py), "--timeout", "30"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for window to appear and capture its PID from stdout
            gui_pid = None
            start_wait = time.time()
            output_captured = []
            while time.time() - start_wait < 30:
                line = proc.stdout.readline()
                if not line:
                    time.sleep(0.5)
                    continue
                output_captured.append(line)
                if "(PID: " in line:
                    import re
                    match = re.search(r"\(PID: (\d+)\)", line)
                    if match:
                        gui_pid = int(match.group(1))
                        break
            
            if not gui_pid:
                # Capture remaining output for debugging
                stdout_remaining, stderr = proc.communicate(timeout=5)
                full_out = "".join(output_captured) + stdout_remaining + stderr
                self.fail(f"Could not capture GUI PID from stdout. Output: {full_out}")

            # Send remote stop
            stop_cmd = ["python3", str(main_py), "stop", str(gui_pid)]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            # Wait for exit with generous timeout
            stdout_rest, stderr = proc.communicate(timeout=30)
            
            all_out = "".join(output_captured) + stdout_rest + stderr
            stop_indicators = ["Terminated", "已终止"]
            self.assertTrue(any(ind in all_out for ind in stop_indicators), f"Expected stop indicator in output: {all_out}")
            self.assertEqual(proc.returncode, 0)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()
