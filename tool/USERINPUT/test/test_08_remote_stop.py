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
        
        test_id = f"test_stop_{int(time.time())}_{os.getpid()}"
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "30", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            time.sleep(2)
            
            stop_cmd = ["python3", str(main_py), "stop", "--id", test_id]
            subprocess.run(stop_cmd, env=env, capture_output=True)
            
            stdout, stderr = proc.communicate(timeout=10)
            
            all_out = stdout + stderr
            stop_indicators = ["Terminated", "已终止"]
            self.assertTrue(any(ind in all_out for ind in stop_indicators))
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

