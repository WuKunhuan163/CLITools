import unittest
import subprocess
import time
import os
from pathlib import Path

class TestBackground(unittest.TestCase):
    def test_run_and_list(self):
        """Test BACKGROUND starting a process and listing it."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        
        if not bg_bin.exists():
            self.skipTest("BACKGROUND bin not found")

        # Start a sleep process
        cmd = [str(bg_bin), "sleep 10"]
        start_result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(start_result.returncode, 0)
        self.assertIn("PID:", start_result.stdout)

        # List processes
        list_result = subprocess.run([str(bg_bin), "--list"], capture_output=True, text=True)
        self.assertIn("sleep 10", list_result.stdout)

if __name__ == '__main__':
    unittest.main()
