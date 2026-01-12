import unittest
import subprocess
import time
import re
from pathlib import Path

class TestBackgroundFlow(unittest.TestCase):
    def test_basic_flow(self):
        """Start, check status, wait, check status."""
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        bg_bin = project_root / "bin" / "BACKGROUND"
        if not bg_bin.exists(): self.skipTest("BACKGROUND bin not found")

        # Start sleep 2
        res = subprocess.run([str(bg_bin), "sleep 2"], capture_output=True, text=True)
        match = re.search(r"PID:?\s*(\d+)", res.stdout)
        self.assertTrue(match, "Failed to get PID from output")
        pid = int(match.group(1))

        # Check status (should be active or completed)
        res = subprocess.run([str(bg_bin), "--status", str(pid)], capture_output=True, text=True)
        self.assertIn(str(pid), res.stdout)

        # Wait
        time.sleep(3)

        # Check status (should be completed)
        res = subprocess.run([str(bg_bin), "--status", str(pid), "--json"], capture_output=True, text=True)
        import json
        data = json.loads(res.stdout)
        self.assertEqual(data["status"]["status"], "completed")

if __name__ == "__main__":
    unittest.main()
