import unittest
import subprocess
import os
import re
from pathlib import Path

class TestBackgroundRun(unittest.TestCase):
    def setUp(self):
        self.project_root = Path("/Applications/AITerminalTools")
        self.bg_bin = self.project_root / "bin" / "BACKGROUND"
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_run_and_pid(self):
        """Verify BACKGROUND run starts a process and returns a PID."""
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "1"], capture_output=True, text=True)
        clean_stdout = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout)
        
        self.assertEqual(res.returncode, 0)
        self.assertIn("Started background process with PID:", clean_stdout)
        
        # Extract PID
        pid_match = re.search(r'PID: (\d+)', clean_stdout)
        self.assertTrue(pid_match, "PID should be present in output")
        pid = pid_match.group(1)
        self.assertTrue(pid.isdigit())

if __name__ == "__main__":
    unittest.main()

