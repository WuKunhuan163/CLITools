import unittest
import subprocess
import time
import os
from pathlib import Path

class TestUserInputRemoteCancel(unittest.TestCase):
    def test_remote_cancel(self):
        """Test remote cancel command."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "USERINPUT" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        proc = subprocess.Popen(["python3", str(main_py), "--timeout", "30", "--id", "test_cancel"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register
            time.sleep(5)
            
            cancel_cmd = ["python3", str(main_py), "cancel", "--id", "test_cancel"]
            subprocess.run(cancel_cmd, env=env, capture_output=True)
            
            stdout, stderr = proc.communicate(timeout=10)
            
            all_out = stdout + stderr
            cancel_indicators = ["Cancelled", "已取消", "已终止", "Terminated"]
            if not any(ind in all_out for ind in cancel_indicators):
                print(f"\nDEBUG: all_out={all_out}")
            self.assertTrue(any(ind in all_out for ind in cancel_indicators))
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

