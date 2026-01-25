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
        
        test_id = f"test_add_time_{int(time.time())}_{os.getpid()}"
        # 2. Start with a medium timeout (10 seconds)
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "10", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register (2 seconds)
            time.sleep(2)
            
            # 3. Send remote add_time (adds 5s -> total ~15s)
            add_time_cmd = ["python3", str(main_py), "add_time", "--id", test_id]
            subprocess.run(add_time_cmd, env=env, capture_output=True)
            
            # 4. Check at 5th second (original timeout 10s would have passed, but added 5s makes it 15s)
            # Actually, original is 10s. We want to check at some point where 10s would have failed.
            time.sleep(10) # 2+10=12s
            
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print(f"\nDEBUG: Process exited prematurely with code {proc.returncode}")
                print(f"DEBUG: stdout={stdout}")
                print(f"DEBUG: stderr={stderr}")
            
            self.assertIsNone(proc.poll(), "Process should still be running at 12s (timeout was 10s, added 5s)")
            
            # 5. Check at 10th second (should have timed out and retrying or exited)
            # Actually, it will retry. We just want to see it didn't exit at 3s.
            
            # Now stop it surgically
            stop_cmd = ["python3", str(main_py), "stop", "--id", test_id]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            proc.communicate(timeout=10)
            
        finally:
            if proc.poll() is None:
                proc.kill()
            # Restore default increment
            subprocess.run(["python3", str(main_py), "config", "--time-increment", "60"], env=env)

if __name__ == '__main__':
    unittest.main()

