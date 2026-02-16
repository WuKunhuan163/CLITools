EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundStop(unittest.TestCase):
    def setUp(self):
        self.project_root = Path("/Applications/AITerminalTools")
        self.bg_bin = self.project_root / "bin" / "BACKGROUND"
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_stop(self):
        """Verify BACKGROUND stop terminates a running process."""
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "10"], capture_output=True, text=True)
        clean_stdout = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout)
        pid = re.search(r'PID: (\d+)', clean_stdout).group(1)
        
        # Verify it shows up in list
        res_list = subprocess.run([str(self.bg_bin), "list"], capture_output=True, text=True)
        self.assertIn(pid, res_list.stdout)
        
        # Stop it
        subprocess.run([str(self.bg_bin), "stop", pid], capture_output=True)
        
        # Verify it is finished
        time.sleep(1)
        res_list = subprocess.run([str(self.bg_bin), "list"], capture_output=True, text=True)
        self.assertIn("finished", res_list.stdout.lower())

if __name__ == "__main__":
    unittest.main()


