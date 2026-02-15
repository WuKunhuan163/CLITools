import unittest
import subprocess
import time
import os
import json
from pathlib import Path

class TestBackgroundTool(unittest.TestCase):
    def setUp(self):
        self.project_root = Path("/Applications/AITerminalTools")
        self.bg_bin = self.project_root / "bin" / "BACKGROUND"
        self.tool_dir = self.project_root / "tool" / "BACKGROUND"
        
        # Ensure tool is clean before each test
        subprocess.run([str(self.bg_bin), "cleanup"], capture_output=True)

    def test_01_run_and_non_blocking(self):
        """Test that run starts a process and returns immediately (non-blocking)."""
        start_time = time.time()
        # Run a command that takes 5 seconds
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "5"], capture_output=True, text=True)
        elapsed = time.time() - start_time
        
        import re
        clean_stdout = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout)
        
        self.assertEqual(res.returncode, 0)
        self.assertIn("Started background process", clean_stdout)
        self.assertLess(elapsed, 1.0, "BACKGROUND run should return immediately")

    def test_02_logging(self):
        """Test that output is correctly captured in logs."""
        test_msg = "hello_background_test"
        res = subprocess.run([str(self.bg_bin), "run", "echo", test_msg], capture_output=True, text=True)
        
        # Give it a moment to finish and write log
        time.sleep(1)
        
        # Find the log file
        log_dir = self.tool_dir / "data" / "log"
        log_files = list(log_dir.glob("*.log"))
        self.assertGreater(len(log_files), 0)
        
        with open(log_files[0], 'r') as f:
            content = f.read()
            self.assertIn(test_msg, content)

    def test_03_wait_functionality(self):
        """Test that wait blocks until the process finishes."""
        # Start a 2-second process
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "2"], capture_output=True, text=True)
        pid = res.stdout.split("PID:")[1].strip().split("\n")[0].strip()
        # Remove ANSI codes if any
        import re
        pid = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', pid)
        
        start_time = time.time()
        subprocess.run([str(self.bg_bin), "wait", pid], capture_output=True)
        elapsed = time.time() - start_time
        
        self.assertGreaterEqual(elapsed, 1.5, "wait should block for at least 1.5 seconds")

    def test_04_stop_and_status(self):
        """Test stopping a process and verifying its status."""
        res = subprocess.run([str(self.bg_bin), "run", "sleep", "10"], capture_output=True, text=True)
        import re
        pid = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', res.stdout.split("PID:")[1].strip().split("\n")[0].strip())
        
        # Verify it's running
        res_list = subprocess.run([str(self.bg_bin), "list"], capture_output=True, text=True)
        self.assertIn(pid, res_list.stdout)
        self.assertIn("sleeping", res_list.stdout.lower())
        
        # Stop it
        subprocess.run([str(self.bg_bin), "stop", pid], capture_output=True)
        
        # Verify it's finished
        time.sleep(1)
        res_list = subprocess.run([str(self.bg_bin), "list"], capture_output=True, text=True)
        self.assertIn("finished", res_list.stdout.lower())

if __name__ == "__main__":
    unittest.main()

