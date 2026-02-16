import unittest
import subprocess
import time
import os
from pathlib import Path

EXPECTED_CPU_LIMIT = 40.0

class TestUserInputRemoteAddTime(unittest.TestCase):
    def test_remote_add_time(self):
        """Test remote add_time command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        # 1. Config increment to 10 seconds (more generous)
        subprocess.run(["python3", str(main_py), "config", "--time-increment", "10"], env=env, check=True)
        
        test_id = f"test_add_time_{int(time.time())}_{os.getpid()}"
        # 2. Start with a medium timeout (15 seconds)
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "15", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register (3 seconds)
            time.sleep(3)
            
            # 3. Send remote add_time (adds 10s -> total ~25s)
            add_time_cmd = ["python3", str(main_py), "add_time", "--id", test_id]
            subprocess.run(add_time_cmd, env=env, capture_output=True)
            
            # 4. Check at 18th second (original timeout 15s would have passed, but added 10s makes it 25s)
            time.sleep(15) # 3+15=18s
            
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                print(f"\nDEBUG: Process exited prematurely at 18s with code {proc.returncode}")
                print(f"DEBUG: stdout={stdout}")
                print(f"DEBUG: stderr={stderr}")
            
            self.assertIsNone(proc.poll(), "Process should still be running at 18s (timeout was 15s, added 10s)")
            
            # Now stop it surgically
            stop_cmd = ["python3", str(main_py), "stop", "--id", test_id]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            proc.communicate(timeout=15)
            
        finally:
            if proc.poll() is None:
                proc.kill()
            # Restore default increment
            subprocess.run(["python3", str(main_py), "config", "--time-increment", "60"], env=env)

if __name__ == '__main__':
    unittest.main()

