import unittest
import subprocess
import time
import os
from pathlib import Path

class TestUserInputRemoteAddTime(unittest.TestCase):
    def test_remote_add_time(self):
        """Test remote add_time command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # Start with a short timeout
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "5", "--id", "test_add_time"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            time.sleep(2)
            
            # Send remote add_time
            add_time_cmd = ["python3", str(main_py), "add_time", "--id", "test_add_time"]
            subprocess.run(add_time_cmd, env=env, capture_output=True)
            
            # If add_time worked, it should NOT exit at 5 seconds
            time.sleep(5)
            self.assertIsNone(proc.poll(), "Process should still be running after adding time")
            
            # Now stop it surgically
            stop_cmd = ["python3", str(main_py), "stop", "--id", "test_add_time"]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            proc.communicate(timeout=10)
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

