EXPECTED_CPU_LIMIT = 60.0
import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundWait(unittest.TestCase):
    def setUp(self):
        self.project_root = Path("/Applications/AITerminalTools")
        self.bg_bin = self.project_root / "bin" / "BACKGROUND" / "BACKGROUND"
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_wait(self):
        """Verify BACKGROUND wait blocks until the process is finished."""
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "2"], capture_output=True, text=True)
        clean_stdout = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout)
        pid = re.search(r'PID: (\d+)', clean_stdout).group(1)
        
        start_time = time.time()
        subprocess.run([str(self.bg_bin), "wait", pid], capture_output=True)
        elapsed = time.time() - start_time
        
        self.assertGreaterEqual(elapsed, 1.5, "Wait should block for the duration of the background process")

if __name__ == "__main__":
    unittest.main()


