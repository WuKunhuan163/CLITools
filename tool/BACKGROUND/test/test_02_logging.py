import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundLogging(unittest.TestCase):
    def setUp(self):
        self.project_root = Path("/Applications/AITerminalTools")
        self.bg_bin = self.project_root / "bin" / "BACKGROUND"
        self.tool_dir = self.project_root / "tool" / "BACKGROUND"
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_logging(self):
        """Verify BACKGROUND captures process output in log files."""
        msg = "background_logging_test_string"
        res = subprocess.run([str(self.bg_bin), "run", "echo", msg], capture_output=True, text=True)
        
        # Extract log path from output
        clean_stdout = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout)
        log_match = re.search(r'Log file: (.*)', clean_stdout)
        self.assertTrue(log_match, "Log file path should be in output")
        log_path = Path(log_match.group(1).strip())
        
        # Wait a moment for process to finish and write log
        time.sleep(1)
        
        self.assertTrue(log_path.exists(), f"Log file {log_path} should exist")
        with open(log_path, 'r') as f:
            content = f.read()
            self.assertIn(msg, content)

if __name__ == "__main__":
    unittest.main()

