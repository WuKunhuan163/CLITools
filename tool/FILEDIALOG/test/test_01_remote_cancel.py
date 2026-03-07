EXPECTED_CPU_LIMIT = 40.0
import unittest
import subprocess
import time
import os
from pathlib import Path

class TestFileDialogRemoteCancel(unittest.TestCase):
    def test_remote_cancel(self):
        """Test remote cancel command for FILEDIALOG."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        test_id = f"test_fd_cancel_{int(time.time())}_{os.getpid()}"
        proc = subprocess.Popen(["python3", str(main_py), "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register
            time.sleep(2)
            
            cancel_cmd = ["python3", str(main_py), "cancel", "--id", test_id]
            subprocess.run(cancel_cmd, env=env, capture_output=True)
            
            stdout, stderr = proc.communicate(timeout=10)
            
            all_out = stdout + stderr
            cancel_indicators = ["Cancelled", "已取消", "已终止", "Terminated", "terminated"]
            self.assertTrue(any(ind.lower() in all_out.lower() for ind in cancel_indicators), 
                            f"Expected cancellation indicator in output: {all_out}")
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

