EXPECTED_CPU_LIMIT = 40.0
import unittest
import subprocess
import time
import os
from pathlib import Path

class TestFileDialogDirectory(unittest.TestCase):
    def test_directory_selection(self):
        """Test directory selection mode for FILEDIALOG."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        main_py = project_root / "tool" / "FILEDIALOG" / "main.py"
        
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_root)
        
        test_id = f"test_fd_dir_{int(time.time())}_{os.getpid()}"
        # Start in directory mode
        proc = subprocess.Popen(["python3", str(main_py), "--directory", "--id", test_id], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
        
        try:
            # Wait for GUI to register
            time.sleep(2)
            
            submit_cmd = ["python3", str(main_py), "submit", "--id", test_id]
            subprocess.run(submit_cmd, env=env, capture_output=True)
            
            stdout, stderr = proc.communicate(timeout=10)
            
            all_out = stdout + stderr
            success_indicators = ["Selected", "已选择"]
            self.assertTrue(any(ind in all_out for ind in success_indicators),
                            f"Expected success indicator in output: {all_out}")
            
        finally:
            if proc.poll() is None:
                proc.kill()

if __name__ == '__main__':
    unittest.main()

