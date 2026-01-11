import unittest
import subprocess
import time
import re
import os
from pathlib import Path

class TestBackgroundList(unittest.TestCase):
    def test_list_report(self):
        """Start several tasks and check the list report."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        if not bg_bin.exists(): self.skipTest("BACKGROUND bin not found")

        # Start 3 tasks
        subprocess.run([str(bg_bin), "sleep 1"], check=True)
        subprocess.run([str(bg_bin), "sleep 5"], check=True)
        subprocess.run([str(bg_bin), "sleep 10"], check=True)

        time.sleep(1)

        # Get list
        res = subprocess.run([str(bg_bin), "--list"], capture_output=True, text=True)
        
        # Extract report path
        match = re.search(r"BACKGROUND_REPORT_PATH: (.*\.md)", res.stdout)
        if not match:
            # Fallback to translated msg if it was clipped
            match = re.search(r": (.*\.md)", res.stdout)
            
        self.assertTrue(match, "Failed to find report path in output")
        report_path = match.group(1).strip()
        self.assertTrue(os.path.exists(report_path), f"Report file {report_path} does not exist")

        with open(report_path, 'r') as f:
            content = f.read()
            self.assertIn("sleep 1", content)
            self.assertIn("sleep 5", content)
            self.assertIn("sleep 10", content)

if __name__ == "__main__":
    unittest.main()
