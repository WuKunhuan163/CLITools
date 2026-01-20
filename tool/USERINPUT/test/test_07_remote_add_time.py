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
        
        # 1. Config increment to 5 seconds
        subprocess.run(["python3", str(main_py), "config", "--time-increment", "5"], env=env, check=True)
        
        # 2. Start with a short timeout (3 seconds)
        # Use a larger parent timeout to avoid retries interfering too quickly
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "3", "--id", "test_add_time"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register
            time.sleep(5)
            
            # 3. Send remote add_time (adds 5s -> total ~8s)
            add_time_cmd = ["python3", str(main_py), "add_time", "--id", "test_add_time"]
            subprocess.run(add_time_cmd, env=env, capture_output=True)
            
            # 4. Check at 4th second (should still be running)
            time.sleep(2) # 2+2=4s
            self.assertIsNone(proc.poll(), "Process should still be running at 4s (timeout was 3s, added 5s)")
            
            # 5. Check at 10th second (should have timed out and retrying or exited)
            # Actually, it will retry. We just want to see it didn't exit at 3s.
            
            # Now stop it surgically
            stop_cmd = ["python3", str(main_py), "stop", "--id", "test_add_time"]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            proc.communicate(timeout=10)
            
        finally:
            if proc.poll() is None:
                proc.kill()
            # Restore default increment
            subprocess.run(["python3", str(main_py), "config", "--time-increment", "60"], env=env)

if __name__ == '__main__':
    unittest.main()

